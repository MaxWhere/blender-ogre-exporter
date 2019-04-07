import bpy
import bmesh
from mathutils import Vector, Matrix


#
# ## utils ##
#


def cc(l) -> list:
    return [l[0], l[2], -l[1]]


#
# ## .mesh ##
#


class Vertex(object):
    """Stores information about a vertex, for a .mesh"""
    
    # Constructor: the purpose of this is to be called in the Mesh object
    def __init__(self,
                 pos,
                 normal,
                 uv=[0, 0],
                 tangent=[0, 0, 0],
                 binormal=[0, 0, 0],
                 rgba=[0, 0, 0],
                 boneweights=None,
                 index=0
                 ):
        self.posd = dict()
        self.nord = dict()
        self.uvd = dict()
        self.tand = dict()
        self.bind = dict()
        self.rgbad = dict()
        
        self.posd["x"], self.posd["y"], self.posd["z"] = pos
        self.nord["x"], self.nord["y"], self.nord["z"] = normal
        
        self.uvd["u"], self.uvd["v"] = uv
        
        self.tand["x"], self.tand["y"], self.tand["z"] = tangent
        self.bind["x"], self.bind["y"], self.bind["z"] = binormal
        
        self.rgbad["r"], self.rgbad["g"], self.rgbad["b"], self.rgbad["a"] = rgba
        
        self.boneweights = boneweights
        
        self.index = index
    
    def __eq__(self, o) -> bool:
        for i in self.posd:
            if self.posd[i] != o.posd[i]:
                return False
        for i in self.nord:
            if self.nord[i] != o.nord[i]:
                return False
        for i in self.uvd:
            if self.uvd[i] != o.uvd[i]:
                return False
        for i in self.tand:
            if self.tand[i] != o.tand[i]:
                return False
        for i in self.bind:
            if self.bind[i] != o.bind[i]:
                return False
        return True


class Mesh(object):
    """Stores mesh information for a .mesh"""
    
    # Constructor
    def __init__(self,
                 obj: bpy.types.Object,
                 depsgraph: bpy.types.Depsgraph,
                 ARMATURE=False,
                 ANIMATION=False
                 ):
        """Constructor that pulls geometry data from bpy"""
        
        # ## ORIG CONSTRUCTOR ##
        
        self.vertexlist = list()
        self.submesh_list = list()
        self.submesh_material = ""
        
        self.vertexcount = 0
        
        self.attr_dict = dict()
        
        self.attr_dict["binormals"] = True
        self.attr_dict["colours_diffuse"] = False
        self.attr_dict["normals"] = True
        self.attr_dict["positions"] = True
        self.attr_dict["tangent_dimensions"] = 3
        self.attr_dict["tangents"] = True
        self.attr_dict["texture_coords"] = 1
        
        # ## END ##
        
        self.name = obj.data.name
        # obj to mesh
        # to_mesh(depsgraph, apply_modifiers, calc_undeformed=False) -> Mesh
        bpymesh = obj.to_mesh(depsgraph, True)
        
        # collect mesh vertices to ogre_types.Vertex
        # triangulate
        self.bmesh_triangulate(bpymesh)
        # update normals, tangents, bitangents
        bpymesh.calc_tangents()
        
        bpy_uvdata = bpymesh.uv_layers.active.data
        
        if bpymesh.vertex_colors.active is not None:
            bpy_color = bpymesh.vertex_colors.active.data
        else:
            bpy_color = None
        
        # Loop through the tris in the triangulated mesh
        for poly in bpymesh.polygons:
            # confirm that what we have is a tri.
            self.is_valid_tri(poly)
            # for tri reference
            tri = list()
            # for every vertex, create an ogre Vertex!
            for index in range(3):
                # get the index of the vertex and the loop
                vert_ref = poly.vertices[index]
                loop_ref = poly.loop_indices[index]
                
                # get the vertex coords, normals, tangent and bitangent
                vc = cc(bpymesh.vertices[vert_ref].co)
                vn = cc(bpymesh.vertices[vert_ref].normal)
                vt = cc(bpymesh.loops[loop_ref].tangent)
                # TODO: confirm this works as binormal
                vb = cc(bpymesh.loops[vert_ref].bitangent)
                
                uv = bpy_uvdata[loop_ref].uv
                
                if bpy_color:
                    rgb = bpy_color[loop_ref].color
                    rgba = [rgb[0], rgb[1], rgb[2], 1]
                else:
                    rgba = [1, 1, 1, 1]
                # TODO: better rgba
                
                # get the bone / vertexgroup influences
                # TODO: confirm this works
                bw = []
                if ARMATURE:
                    for group in bpymesh.vertices[vert_ref].groups:
                        if group.weight > 0.01:
                            vg = obj.vertex_groups[group.group]
                            bw[vg.name] = group.weight
                
                # create vertex
                vert = Vertex(vc, vn, uv=uv, tangent=vt, binormal=vb, rgba=rgba, boneweights=bw)
                
                # add the Vertex to our list in the Mesh, and to the tri
                tri.append(self.add_vertex(vert))
            
            # for every poly (tri) add a tri to our submesh list
            self.add_sm_tri(tri)
        
        # we go back to our object
        
        # and get that material!
        self.pull_sm_material(obj)
        
        if ANIMATION:
            # TODO: export poses
            # ... and anims
            pass
            
    def pull_sm_material(self, obj) -> None:
        # get the material name
        material = obj.name
        if len(obj.data.materials) > 0:
            material = obj.data.materials[0].name
        # and set it as the material of the mesh.
        self.submesh_material = material
    
    def add_sm_tri(self, tri):
        # let's see if it's really a tri
        if len(tri) != 3:
            raise ValueError("Tri not a tri!")
        else:
            # if so, then add it to our list
            self.submesh_list.append(tri)
    
    # TODO: REVIEW
    def add_vertex(self, vertex) -> int:
        if vertex in self.vertexlist:
            return self.vertexlist[self.vertexlist.index(vertex)].index
        else:
            # assign the vertex an index first come first served
            vertex.index = len(self.vertexlist)
            # and add it to the list
            self.vertexlist.append(vertex)
            # return the index so we can build tris
            self.vertexcount += 1
            return vertex.index
    
    def bmesh_triangulate(self, bpy_mesh) -> None:
        bm = bmesh.new()
        bm.from_mesh(bpy_mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(bpy_mesh)
        bm.free()
    
    def is_valid_tri(self, poly):
        if len(poly.vertices) != 3:
            raise ValueError("Polygon not a tri!")


#
# ## .scene ##
#


class Node(object):
    """Stores information for a node (obj) in a .scene"""
    
    # Constructor
    def __init__(self, obj: bpy.types.Object, meshfile, PHYSICS=False):
        """Pull data for a node in a .scene"""
        
        # TODO:
        # obj mass
        
        name = obj.name
        pos = cc(obj.location)
        quad = obj.rotation_quaternion
        scale = obj.scale
        scale = [scale[0], scale[2], scale[1]]
        
        # Name
        self.name = name
        
        # Stuff ne *need* to know
        self.posd = dict()
        self.quad = dict()
        self.scaled = dict()
        
        self.posd["x"], self.posd["y"], self.posd["z"] = pos
        self.quad["qw"], self.quad["qx"], self.quad["qy"], self.quad["qz"] = quad
        self.scaled["x"], self.scaled["y"], self.scaled["z"] = scale
        
        self.ent_dict = dict()
        
        self.ent_dict["meshFile"] = meshfile
        self.ent_dict["name"] = name
        
        # Actor?
        self.ent_dict["actor"] = False
        
        # Physics
        self.set_physics_properties()
        
        # ???
        self.ghost = False
        
        # ## END ##
        
        # hide_render, hide_select, hide_veiwport as self.ghost?
        
        # If we have physics export enabled
        if PHYSICS:
            # We do physics stuff.
            # TODO: get physics properties
            # obj.collision
            self.set_physics_properties()
    
    def set_physics_properties(self,
                               physics_type="STATIC",
                               aniso_friction=False,
                               damping_rot=0,
                               damping_trans=0,
                               friction_matrix=[1, 1, 1],
                               inertia_tensor=0,
                               lock_rot_matrix=[False, False, False],
                               lock_trans_matrix=[False, False, False],
                               mass=1,
                               mass_radius=1,
                               velocity_max=0,
                               velocity_min=0
                               ) -> None:
        
        self.ent_dict["physics_type"] = physics_type
        
        self.ent_dict["anisotropic_friction"] = aniso_friction
        
        self.ent_dict["damping_rot"] = damping_rot
        self.ent_dict["damping_trans"] = damping_trans
        
        self.ent_dict["friction_x"], self.ent_dict["friction_y"], self.ent_dict["friction_z"] = friction_matrix
        
        self.ent_dict["inertia_tensor"] = inertia_tensor
        
        self.ent_dict["lock_rot_x"], self.ent_dict["lock_rot_y"], self.ent_dict["lock_rot_z"] = lock_rot_matrix
        self.ent_dict["lock_trans_x"], self.ent_dict["lock_trans_y"], self.ent_dict["lock_trans_z"] = lock_trans_matrix
        
        self.ent_dict["mass"] = mass
        self.ent_dict["mass_radius"] = mass_radius
        
        self.ent_dict["velocity_max"] = velocity_max
        self.ent_dict["velocity_min"] = velocity_min


class Scene(object):
    """Stores information about the scene, for the .scene"""
    
    # Constructor
    def __init__(self, scene):
        """The constructor to call"""
        
        v3ds = scene.display.shading
        # TODO: v3ds.background_type to decide background type.
        bgc = v3ds.background_color
        # bgc = [0.05, 0.05, 0.05]
        
        self.nodes = list()
        self.materials = list()
        
        # ALL OF THESE
        # have to be strings, as they are root, and they aren't sanitized
        self.export_time = "0"
        self.exported_by = "Default"
        self.formatVersion = "1.0.1"
        self.previous_export_time = "0"
        
        self.set_environment(colourAmbient=[0, 0, 0], colourBackground=bgc, colourDiffuse=[0.05, 0.05, 0.05])
    
    def add_node(self, Node) -> None:
        self.nodes.append(Node)
    
    def add_material(self, Material) -> None:
        self.materials.append(Material)
    
    def set_environment(self,
                        colourAmbient=[0, 0, 0],
                        colourBackground=[0.05, 0.05, 0.05],
                        colourDiffuse=[0.05, 0.05, 0.05]
                        ) -> None:
        self.colourAmbient = colourAmbient
        self.colourBackground = colourBackground
        self.colourDiffuse = colourDiffuse


#
# ## .material ##
#


class Material(object):
    """Stores information on a material, for the .material"""
    
    # Constructor
    def __init__(self, material):
        
        # TEMP: set diffuse to none
        self.diffuse = None
        
        # if we have a material that's using nodes (we have to have)
        if material.use_nodes:
            node_principled = None
            
            # get the Principled node
            # unsafe (there may be multiple, or it may not exist)
            node_principled = material.node_tree.nodes["Principled BSDF"]
            if node_principled is not None:
                # try to get the image-texture node (unsafe again)
                tex_node = None
                if len(node_principled.inputs["Base Color"].links):
                    tex_node = node_principled.inputs["Base Color"].links[0].from_node
                
                # if we have it, let's get the image file path
                # otherwise just sove a color into the duffuse property.
                if tex_node is not None:
                    if tex_node.image.is_dirty:
                        tex_node.image.save_as()
                    tu_texture = tex_node.image.filepath
                else:
                    tu_texture = None
                    r, g, b, a = node_principled.inputs["Base Color"].default_value
                    self.diffuse = [r, g, b, a]
            else:
                raise ReferenceError("No Principled BSDF node found.")
        else:
            raise ReferenceError("No material nodes found.")
        
        self.name = material.name
        
        # currently we're setting everything to default values
        # later this may change
        self.receive_shadows = "on"
        
        self.ambient = [0.8, 0.8, 0.8, 1.0]
        if self.diffuse is None:
            self.diffuse = [0.65, 0.65, 0.65, 1.0]
        self.specular = [0.5, 0.5, 0.5, 1.0, 12.5]
        self.emissive = [0.0, 0.0, 0.0, 1.0]
        
        # pass
        self.pass_dict = dict()
        
        self.pass_dict["alpha_to_coverage"] = "off"
        self.pass_dict["colour_write"] = "on"
        self.pass_dict["cull_hardware"] = "clockwise"
        self.pass_dict["depth_check"] = "on"
        self.pass_dict["depth_func"] = "less_equal"
        self.pass_dict["depth_write"] = "on"
        self.pass_dict["illumination_stage"] = ""
        self.pass_dict["light_clip_planes"] = "off"
        self.pass_dict["light_scissor"] = "off"
        self.pass_dict["lighting"] = "on"
        self.pass_dict["normalise_normals"] = "off"
        self.pass_dict["polygon_mode"] = "solid"
        self.pass_dict["scene_blend"] = "one zero"
        self.pass_dict["scene_blend_op"] = "add"
        self.pass_dict["shading"] = "gouraud"
        self.pass_dict["transparent_sorting"] = "on"
        
        # texture_unit
        self.tu_dict = dict()
        
        self.tu_dict["texture"] = tu_texture
        self.tu_dict["tex_address_mode"] = "wrap"
        self.tu_dict["scale"] = "1.0 1.0"
        self.tu_dict["colour_op"] = "modulate"
        
        pass


#
# ## .skeleton ## (?)
#


class Bone(object):
    """A Bone. It spook."""
    
    def __init__(self, name, parentbone):
        self.name = name
    
    # TODO: bone id


class Skeleton(object):
    """A Skeleton. It spook even more."""
    
    def __init__(self, arg):
        self.arg = arg
    
    # TODO: verify
