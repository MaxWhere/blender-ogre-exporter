import os
import subprocess
import inspect
import shutil

# from mathutils import Matrix, Vector, Color
# from bpy_extras import io_utils, node_shader_utils

import bpy
from bpy_extras.wm_utils.progress_report import (ProgressReport, ProgressReportSubstep)

from . import ogre_types
from . import zxml
from . import zmat


#
# ## Short functional funcs ##
#


def name_convert(name) -> str:
    """Convert names to be *everything* compatible"""
    if name is None:
        return 'None'
    else:
        return name.replace(' ', '_')


#
# ## Save ##
#


def save(context,
         filepath,
         *,
         export_armature,
         export_animation,
         export_physics,
         export_materials,
         do_binary
         ) -> set:
    """
    The main function called from __init__.py to save the scene
    """
    
    import time
    time_start = time.time()
    
    write_loop(context, filepath,
               ARMATURE=export_armature,
               ANIMATION=export_animation,
               PHYSICS=export_physics,
               MATERIALS=export_materials,
               BINARY=do_binary
               )
    
    print("BOE finished: %.4f sec" % (time.time() - time_start))
    
    # Return finished state; if we had errors, it would yield a traceback anyway.
    return {'FINISHED'}


#
# ## Write call ##
#


def write_loop(context, filepath,
               ARMATURE,
               ANIMATION,
               PHYSICS,
               MATERIALS,
               BINARY
               ) -> None:
    """
    Func for looping write calls + setting up env for writing
    """
    
    with ProgressReport(context.window_manager) as progress:
        base_name, ext = os.path.splitext(filepath)
        # base_name = name_convert(base_name) << this 'ere probably causes problems with windows.
        
        full_path = [base_name, '', '', ext]  # Base name, scene name, frame number, extension
        
        bpy_depsgraph = context.depsgraph
        bpy_scene = context.scene
        
        # Dirty (!) fix for the 'object with/ mesh' problem
        tmp_bo = list()
        bpy_objects = bpy_scene.objects
        for tmp_obj in bpy_objects:
            print(str(type(tmp_obj.data)))
            print(type(tmp_obj.data))
            if (str(type(tmp_obj.data)) == "<class 'bpy_types.Mesh'>"):
                tmp_bo.append(tmp_obj)
            tmp_obj = None
        bpy_objects = tmp_bo
        tmp_bo = None
        
        if not len(bpy_objects):
            raise Exception("There is nothing to export.")
        
        # Exit edit mode before exporting, so current object states are exported properly.
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # We only want to export one frame currently, so:
        frame = bpy_scene.frame_current
        bpy_scene.frame_set(frame, subframe=0.0)
        
        #
        # ## pull data from bpy, create file paths, ect ##
        #
        
        og_scene = ogre_types.Scene(bpy_scene)
        og_meshes = dict()
        og_materials = dict()
        # og_armatures = dict()
        
        path_scene = ""
        path_mesh = ""
        
        bpy_exported_meshes = dict()
        og_exported_meshes = dict()
        
        # progress: number of objects to export
        progress.enter_substeps(len(bpy_objects))
        
        # iterate through our objects
        for obj in bpy_objects:
            # !! "dependancies"
            mesh_name = str(obj.data.name)
            
            material = obj.active_material
            if material is None:
                try:
                    material = obj.material_slots.values()[0].material
                except ReferenceError("Material not found. Do your objects have materials, that use nodes?") as e:
                    raise e
            
            material_name = material.name
            # skeleton_name =
            
            # !! calculate paths
            # basically adding the parts of full_path together
            path_scene = full_path[0] + full_path[1] + full_path[2] + full_path[3]
            path_mesh = full_path[0] + full_path[1] + full_path[2] + "_" + mesh_name + ".mesh"
            path_material = full_path[0] + full_path[1] + full_path[2] + ".material"
            # path_armature = full_path[0] + full_path[1] + full_path[2] + "_" + skeleton_name + ".skeleton"
            
            # !! Mesh
            # MESH EXPORT GUARD
            tmp_mesh = obj.to_mesh(bpy_depsgraph, True)
            cur_mesh = None
            
            # for each mesh in the exported meshes (and materials)
            for key_path_mesh in bpy_exported_meshes:
                # we get the (already done) mesh data and material name (unique ID)
                cmp_mesh, cmp_mat = bpy_exported_meshes[key_path_mesh]
                # if we find that both match the current object's (dupli obj)
                if (cmp_mesh.unit_test_compare(mesh=tmp_mesh) == "Same") and (cmp_mat == material_name):
                    # then we redirect to said (already exported) mesh data
                    path_mesh = key_path_mesh
                    cur_mesh = og_exported_meshes[key_path_mesh]
                    # modify mesh_name here to avoid problems with nodes in .scene
                    junk, mesh_name = os.path.split(path_mesh)
            
            # if we DIDN'T find a siutable (duplicate) datablock
            if cur_mesh is None:
                # we put the current contender into the 'exported' container (along with its material)
                bpy_exported_meshes[path_mesh] = tmp_mesh, material_name
                # then get it's data. we need data.
                og_exported_meshes[path_mesh] = cur_mesh = ogre_types.Mesh(obj, bpy_depsgraph, ARMATURE, ANIMATION)
                # modify mesh_name here to avoid problems with nodes in .scene
                junk, mesh_name = os.path.split(path_mesh)
            
            # !! Material
            if MATERIALS:
                # materials only guard against one material twice as they have different logic than meshes.
                # which is kinda bs.
                if material_name not in og_materials.keys():
                    og_materials[material_name] = ogre_types.Material(material)
            
            # !! put collected stuff into lists for writing
            
            cur_node = ogre_types.Node(obj, meshfile=mesh_name, PHYSICS=PHYSICS)
            
            og_meshes[path_mesh] = cur_mesh
            og_scene.add_node(cur_node)
            
            # progress: step per each object
            progress.step()
        
        # progress: first batch done (collection of data)
        progress.leave_substeps()
        
        #
        # ## create files, serialize xml, ect ##
        #
        
        # initialize the xml-builder for scene
        xn_scene = zxml.XMLnode()
        # and the serializer
        seri = zxml.XMLserializer()
        
        # ## .scene ##
        
        xn_scene.append("scene", {
                        "export_time": og_scene.export_time,
                        "exported_by": og_scene.exported_by,
                        "formatVersion": og_scene.formatVersion,
                        "previous_export_time": og_scene.previous_export_time
                        })
        
        xn_scene.add("nodes", {})
        first = True
        for node in og_scene.nodes:
            if first:
                xn_scene.add("node", {"name": node.name})
                first = False
            else:
                xn_scene.append("node", {"name": node.name})
            
            xn_scene.add("position", node.posd)
            xn_scene.append("rotation", node.quad)
            xn_scene.append("scale", node.scaled)
            xn_scene.append("game", {})
            xn_scene.add("sensors", {})
            xn_scene.append("actuators", {})
            xn_scene.pointer_up()
            xn_scene.append("entity", node.ent_dict)
            xn_scene.pointer_up()
        
        xn_scene.pointer_up()
        
        if MATERIALS:
            xn_scene.add("externals", {})
            xn_scene.add("item", {"type": "material"})
            xn_scene.add("file", {"name": path_material})
            xn_scene.pointer_up()
            xn_scene.pointer_up()
            xn_scene.pointer_up()
        
        xn_scene.add("environment", {})
        col = og_scene.colourAmbient
        xn_scene.add("colourAmbient", {"r": col[0], "g": col[1], "b": col[2]})
        col = og_scene.colourBackground
        xn_scene.append("colourBackground", {"r": col[0], "g": col[1], "b": col[2]})
        col = og_scene.colourDiffuse
        xn_scene.append("colourDiffuse", {"r": col[0], "g": col[1], "b": col[2]})
        
        seri.write_file(path_scene, graph=xn_scene.graph)
        
        # ## .material ##
        
        if MATERIALS:
            
            # progress: cycle thru materials
            progress.enter_substeps(len(og_materials))
            
            mn_mat = zmat.MATnode()
            seri_mat = zmat.MATserializer()
            
            mn_mat.bracket("material", "_missing_material_")
            mn_mat.entry("receive_shadows", "off")
            mn_mat.bracket("technique", "")
            mn_mat.bracket("pass", "")
            
            mn_mat.entry("ambient", "0.1 0.1 0.1 1.0")
            mn_mat.entry("diffuse", "0.8 0.0 0.0 1.0")
            mn_mat.entry("specular", "0.5 0.5 0.5 1.0 12.5")
            mn_mat.entry("emissive", "0.3 0.3 0.3 1.0")
            
            mn_mat.pointer_reset()
            
            for material_name in og_materials:
                og_material = og_materials[material_name]
                
                mn_mat.bracket("material", og_material.name)
                mn_mat.entry("receive_shadows", og_material.receive_shadows)
                mn_mat.bracket("technique", "")
                mn_mat.bracket("pass", og_material.name)
                
                mn_mat.entry("ambient", og_material.ambient)
                mn_mat.entry("diffuse", og_material.diffuse)
                mn_mat.entry("specular", og_material.specular)
                mn_mat.entry("emissive", og_material.emissive)
                
                # like hell am I gonna write down all that once again
                for et in og_material.pass_dict:
                    at = og_material.pass_dict[et]
                    mn_mat.entry(et, at)
                # fk no.
                
                if og_material.tu_dict["texture"] is not None:
                    path_img = og_material.tu_dict["texture"]
                    tmp = bpy.path.basename(path_img)
                    og_material.tu_dict["texture"] = tmp
                    
                    src = bpy.path.abspath(path_img)
                    dst = os.path.join(os.path.dirname(path_material), tmp)
                    if src != dst:
                        shutil.copyfile(src, dst)
                    
                    mn_mat.bracket("texture_unit", "")
                    for et in og_material.tu_dict:
                        at = og_material.tu_dict[et]
                        mn_mat.entry(et, at)
                
                mn_mat.pointer_reset()
                
                # progress: step per each mat
                progress.step()
            
            # progress: done with mats
            progress.leave_substeps()
            
            seri_mat.write_file(path_material, mn_mat.graph)
        
        # ## .xml.mesh, .mesh ##
        
        # progress: go for meshes
        if BINARY:
            # binary takes two steps
            progress.enter_substeps(len(og_meshes) * 2)
        else:
            # otherwise we just have one
            progress.enter_substeps(len(og_meshes))
        
        for path_mesh in og_meshes:
            og_mesh = og_meshes[path_mesh]
            
            # initialize xml-builder
            xn_mesh = zxml.XMLnode()
            
            # Roots
            xn_mesh.append("mesh", {})
            xn_mesh.add("sharedgeometry", {"vertexcount": og_mesh.vertexcount})
            xn_mesh.add("vertexbuffer", og_mesh.attr_dict)
            
            # Vertices
            first = True
            for vert in og_mesh.vertexlist:
                if first:
                    xn_mesh.add("vertex", {})
                    first = False
                else:
                    xn_mesh.append("vertex", {})
                xn_mesh.add("position", vert.posd)
                xn_mesh.append("normal", vert.nord)
                xn_mesh.append("texcoord", vert.uvd)
                xn_mesh.append("tangent", vert.tand)
                xn_mesh.append("binormal", vert.bind)
                xn_mesh.pointer_up()
            xn_mesh.pointer_up()
            xn_mesh.pointer_up()
            xn_mesh.append("submeshes", {})
            xn_mesh.add("submesh", {
                        "material": og_mesh.submesh_material,
                        "operationtype": "triangle_list",
                        "use32bitindexes": "False",
                        "usesharedvertices": "true"
                        })
            xn_mesh.add("faces", {"count": len(og_mesh.submesh_list)})
            
            # Tris
            first = True
            for tri in og_mesh.submesh_list:
                if first:
                    xn_mesh.add("face", {"v1": tri[0], "v2": tri[1], "v3": tri[2]})
                    first = False
                else:
                    xn_mesh.append("face", {"v1": tri[0], "v2": tri[1], "v3": tri[2]})
            xn_mesh.pointer_up()
            xn_mesh.pointer_up()
            xn_mesh.pointer_up()
            xn_mesh.append("submeshnames", {})
            xn_mesh.add("submesh", {"index": 0, "name": og_mesh.submesh_material})
            xn_mesh.pointer_up()
            seri.write_file(path_mesh + ".xml", graph=xn_mesh.graph)
            
            # progress: done with a mesh
            progress.step()
            
            # ## .mesh ##
            # Binary creation:
            if BINARY:
                # get current path
                fn = inspect.getframeinfo(inspect.currentframe()).filename
                path = os.path.dirname(os.path.abspath(fn))
                # construct command
                oxt_cmd = path + "/ogrexmltools/OgreXMLConverter.exe -d3d -q " + path_mesh + ".xml " + path_mesh
                # print("XML_Converter cmd: " + oxt_cmd)
                
                # execute command
                oxt_proc = subprocess.Popen(oxt_cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # print converter output
                out, err = oxt_proc.communicate()
                out = out.decode()
                err = err.decode()
                print(out)
                print(err)
                
                # progress: done with a mesh's binary
                progress.step()
        
        # progress: done with meshes
        progress.leave_substeps()
        
        # ## END OF WRITE_LOOP ##
