import os


#
# ## MATnode class (to create serializable structure while keeping sanity) ##
#

# SEE zxml.py FOR EXTRA NOTES

class MATnode(object):
    """Create serializable material structure, while keeping your sanity"""
    
    def __init__(self):
        self.graph = []
        self.pp = self.graph
        self.lp = self.graph
        self.level = 0
    
    def entry(self, name="", attr="") -> None:
        """Append entry to current level (parent)"""
        # [ {"name": [pptr, attr, level, -[]- ]} ]
        ptr = self.pp
        lv = self.level
        self.lp.append({name: [ptr, attr, lv]})
    
    def bracket(self, name="", attr="") -> None:
        """Add a bracket to current level"""
        # [ {"name": [pptr, attr, level, -[]- ]} ]
        ptr = self.lp
        lv = self.level
        self.lp.append({name: [ptr, attr, lv, []]})
        self.pp = self.lp
        self.lp = self.lp[len(self.lp) - 1][name][3]
        self.level += 1
    
    def pointer_up(self) -> None:
        """Move the current level pointer up."""
        self.lp = self.pp
        for name in self.lp[len(self.lp) - 1]:
            self.pp = self.lp[len(self.lp) - 1][name][0]
            break
        self.level -= 1
    
    def pointer_reset(self) -> None:
        """Move the current level pointer to root"""
        self.pp = self.graph
        self.lp = self.graph
        self.level = 0


#
# ## Serializer class (to write uniform-looking files) ##
#


class MATserializer(object):
    """Class for serializing materials"""
    
    def __init__(self, ind="    "):
        self.ind = ind
    
    def sanitize(self, attr):
        if (type(attr) is not str) and (type(attr) is not list):
            attr = str(attr)
        elif type(attr) is list:
            atb = ""
            for at in attr:
                atb += str(at) + " "
            attr = atb
        return attr
    
    def serialize(self, graph):
        seri = ""
        for node in graph:
            
            # [ {"name": [pptr, attr, level, -[]- ]} ]
            
            name = data = None
            for name in node:
                data = node[name]
                break
            
            # "name"
            # [pptr, attr, level, -[]- ]
            
            # it's an entry
            if len(data) == 3:
                ptr, attr, level = data
                
                attr = self.sanitize(attr)
                
                ind = str(self.ind * level)
                seri += (ind + name + " " + attr + "\n")
            
            # it's a bracket
            elif len(data) == 4:
                
                ptr, attr, level, cgraph = data
                
                attr = self.sanitize(attr)
                
                ind = str(self.ind * level)
                seri += (ind + name + " " + attr + "\n")
                seri += (ind + "{\n")
                
                if len(cgraph):
                    seri += (self.serialize(cgraph))
                
                seri += (ind + "}\n")
            else:
                raise LookupError("Material 'data' block mismatch.")
        
        return seri
    
    def write_file(self,
                   filepath,
                   graph=[],
                   ) -> None:
        """
        Basic write function. Getting them xmls written.
        """
        
        seri_string = "// Material generated by BOE\n\n"
        seri_string += self.serialize(graph)
        
        # And finally!
        with open(filepath, mode="w", encoding="UTF-8") as fw:
            fw.write(seri_string)