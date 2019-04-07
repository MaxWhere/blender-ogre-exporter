# Blender Ogre Export

### BOE

The goal of this project is to create a blender addon, that is capable of exporting scenes for the [OGRE](https://github.com/OGRECave/ogre/) engine

**Warning: the project is currently in development, prone to breaking, and generally considered unsafe. Use with that in mind.**

### Install:

Compress the `io_ogre` folder to a .zip, and install it through blender's addon manager.

### Use:

Upon activating, the option to export OGRE scenes (.scene) appears in the export menu. Works just like any other exporter. No weird switches or other bs to screw up your workflow. In the future it will (hopefully) support arbitrary scene export, with almost no limitations.

While working on this addon, I took inspiration and ideas from;
- [Kenshi mesh exporter by 'someone'](https://www.lofigames.com/phpBB3/viewtopic.php?f=11&t=10732&p=58230)
- Ogre resources:
	- https://github.com/OGRECave/ogre/blob/master/OgreMain/src/OgreMeshSerializerImpl.cpp
	- https://github.com/OGRECave/ogre/tree/master/Tools/XMLConverter/docs
	- https://github.com/OGRECave/DotSceneFormat
- [blender2ogre](https://github.com/OGRECave/blender2ogre)
- [Wavefront OBJ io for blender](https://docs.blender.org/manual/en/dev/addons/io_obj.html)

Shoutout to the mentioned above, and the folk at blender community discord! Thank you all.
