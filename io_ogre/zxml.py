import os
import xml.etree.ElementTree as et


#
# ## XMLnode class (to create serializable structure while keeping sanity) ##
#


class XMLnode(object):
    """Create serializable xml structure, while keeping your sanity"""
    
    def __init__(self):
        self.graph = []
        self.pp = self.graph
        self.lp = self.graph
        self.cp = self.graph
    
    def append(self, name="", attr={}) -> None:
        """Append nodes to the current level (parent)"""
        # append a new node to the current level
        ptr = self.pp
        self.lp.append({name: [ptr, attr, []]})
        # move cp to point at the data block of the last appended node
        #          get   |  current last  | name | datablock is always third (2)
        self.cp = self.lp[len(self.lp) - 1][name][2]
    
    def add(self, name="", attr={}) -> None:
        """Add a sub-node to the last added node"""
        # add the new node to the last added's datablock
        ptr = self.lp
        self.cp.append({name: [ptr, attr, []]})
        # set pp to be on the previous (parent) level
        self.pp = self.lp
        # set lp to be on the level we just added to
        self.lp = self.cp
        # same as before
        # set cp to point at the last added's datablock.
        self.cp = self.lp[len(self.lp) - 1][name][2]
    
    def pointer_up(self) -> None:
        """Move the current level pointer up."""
        # not necessarily the best idea
        self.cp = self.lp
        # sounds a tad better
        self.lp = self.pp
        # get the name of the (only one) node in the last dict we know about.
        for name in self.lp[len(self.lp) - 1]:
            # set pp (parent) to be the same as the parent pointer in the data
            self.pp = self.lp[len(self.lp) - 1][name][0]
            break


#
# ## Serializer class (to write uniform-looking files) ##
#


class XMLserializer(object):
    """Class for serializing xml"""
    
    def __init__(self, ind="\t"):
        self.ind = ind
    
    def indent(self, elem, level=0):
        ind = self.ind
        i = "\n" + level * ind
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + ind
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for element in elem:
                self.indent(element, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    
    def serialize(self, root, graph):
        for node in graph:
            
            # """ {"nodes": [ptr, {}, [{"name": [{}, []]}]]} """
            
            name = data = None
            for name in node:
                data = node[name]
                break
            
            # """ nodes """
            # """ [ptr, {}, [{"name": [{}, []]}]] """
            
            if len(data):
                ptr, attr, cgraph = data
                
                for at in attr:
                    if type(attr[at]) is float:
                        attr[at] = f"{attr[at]:.6f}"
                    if type(attr[at]) is not str:
                        attr[at] = str(attr[at])
                # """ [{"name": [{}, []]}] """
                
                croot = et.SubElement(root, name, attr)
                if len(cgraph):
                    self.serialize(croot, cgraph)
    
    def write_file(self,
                   filepath,
                   graph=[],
                   ) -> None:
        """
        Basic write function. Getting them xmls written.
        """
        
        # TODO:
        # Initialize string to write with header
        # xmlstr = str("<!-- Blender v%s OGRE File: %r -->\n" % (bpy.app.version_string, os.path.basename(bpy.data.filepath)))
        # xmlstr += str("<!-- www.blender.org - github.com/OGRECave -->\n\n")
        
        # """ {"scene": [ptr, {attr}, []]} """
        
        root_name = root_data = None
        for root_name in graph[0]:
            root_data = graph[0][root_name]
            break
        
        root = et.Element(root_name, root_data[1])
        tree = et.ElementTree(root)
        
        self.serialize(root, root_data[2])
        
        self.indent(root)
        
        # And finally!
        with open(filepath, mode="w", encoding="UTF-8"):
            # "ugly" printing of xml, sadly "pretty" is hard.
            tree.write(filepath, encoding="UTF-8")
