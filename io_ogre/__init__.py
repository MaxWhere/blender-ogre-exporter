# license
# block
# goes
# here


bl_info = {
    "name": "Blender OGRE Exporter (.scene, .mesh, .material)",
    "author": "Zaki",
    "version": (0, 1, 2),
    "blender": (2, 80, 0),
    "location": "File > Export...",
    "description": "Export to Ogre xml and binary formats",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"
}


import bpy
from bpy.props import (
        BoolProperty,
        FloatProperty,
        StringProperty,
        EnumProperty
        )
from bpy_extras.io_utils import (
        ExportHelper,
        orientation_helper,
        path_reference_mode,
        axis_conversion
        )


#
# ## Declare functional classes ##
#


class BOE_OT_scene_export(bpy.types.Operator, ExportHelper):
    """docstring for BOE_OT_scene_export."""
    
    bl_idname = "export_ogre_scene.scene"
    bl_label = 'Export OGRE .scene'
    bl_options = {'PRESET'}
    
    filename_ext = ".scene"
    
    export_armature: BoolProperty(
            name="Armature",
            description="export bones and bone weights",
            default=False,
            )
    
    export_animation: BoolProperty(
            name="Animation",
            description="export animation frames",
            default=False,
            )
    
    export_physics: BoolProperty(
            name="Physics",
            description="export physics properties",
            default=True,
            )
    
    export_materials: BoolProperty(
            name="Materials",
            description="export materials",
            default=True,
            )
    
    do_binary: BoolProperty(
            name="Binary files",
            description="create ogre-specific binary files",
            default=True,
            )
    
    def execute(self, context):
        from . import ogre_export
        
        keywords = self.as_keywords(ignore=("check_existing",
                                            "filter_glob",
                                            ))
        
        return ogre_export.save(context, **keywords)


# ## DEPRECATED ##

class BOE_OT_mesh_export(bpy.types.Operator, ExportHelper):
    """docstring for BOE_OT_mesh_export."""
    
    bl_idname = "export_ogre_mesh.mesh"
    bl_label = 'Export OGRE .mesh'
    bl_options = {'PRESET'}
    
    filename_ext = ".mesh"
    
    example_toggle: BoolProperty(
            name="Example toggle",
            description="this is an example of a toggle option when exporting",
            default=True,
            )
    
    def execute(self, context):
        from . import ogre_export
        
        return ogre_export.save(context)


#
# ## Listing classes, preparing for registering ##
#


def menu_func_export(self, context):
    self.layout.operator(BOE_OT_scene_export.bl_idname, text="OGRE (.scene)")
    # self.layout.operator(BOE_OT_mesh_export.bl_idname, text="OGRE (.mesh)")


classes = (
    BOE_OT_scene_export,
    BOE_OT_mesh_export
)


#
# ## Registering loop ##
#


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
