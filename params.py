import os
from collections import defaultdict
from misc import join_with_underscores

class Tree(defaultdict):
    """General purpose tree.
    
    Access is via indexing e.g.
        t=Tree()
        t['type']='farm'
        t['cows']['breed']='Hereford'
        
    Implementation uses autovivification property of defaultdict:
    https://en.wikipedia.org/wiki/Autovivification
    """
    def __init__(self,**kwargs):
        """Create tree with nodes defined in kwargs."""
        defaultdict.__init__(self,type(self),**kwargs)
    
    @classmethod
    def compare(cls,nodes):
        """Compare trees.
        
        Args:
            nodes (iterable of cls): trees to compare 
            
        Returns:
            tuple: contains (common, onlys) where common (cls) is a tree
                containing nodes common to all, and onlys is a list of length
                len(nodes) containing differences
        """
        values=[cls.node_value(node) for node in nodes]
        if all(values[0]==value for value in values):
            # All nodes identical
            return nodes[0],None
        elif all(isinstance(value,cls) for value in values):
            # All nodes are instances of the tree class
            common=cls()
            onlys=[cls() for n in range(len(values))]
            for key in set.union(*[set(value.keys()) for value in values]):
                if all(key in value for value in values):
                    # key present in all nodes/subtrees, so compare them (recursively)
                    c,os=cls.compare([value[key] for value in values])
                    if c is not None:
                        common[key]=c
                    if os is not None:
                        for only,o in zip(onlys,os):
                            only[key]=o
                else:
                    # Key not present in all nodes/subtrees, so distribute to the onlys
                    for only,value in zip(onlys,values):
                        if key in value.keys():
                            only[key]=value[key]
            if len(onlys)==0:
                # They were identical. In this case, we may preserve the 
                # meta-data
                common=nodes[0]
            return common,onlys
        else:
            return None,nodes
        
    def compare_to(self,node2):
        """Compare this tree with another.
        
        Convenience wrapper for Tree.compare.
        """
        return self.compare([self,node2])
        
    @classmethod
    def node_value(cls,node):
        """Return the value of a node for comparison purposes. This allows metadata
        to be attached without affecting comparisons."""
        return node
        
def string_to_path(string):
    return string.replace(os.sep,'-').replace(' ','_')
      
class ParameterTree(Tree):
    """Nodes can be any class, including ParameterTree. A special classes is
    ParameterTree.Entry. This allows metadata (such as compact path representation)
    to be attached to a node. This metadata is preserved, where possible, during
    tree comparison."""
    class Entry:
        def __init__(self,value,path=None):
            """Value can be any classs. ParameterTree and ParameterTree.Entry (copy
            constructor) are handled sensibly."""
            if isinstance(value,ParameterTree.Entry):
                value,path=value.value,value.path
            self.value=value
            # if string is None:
            #     string=value.string() if isinstance(value,ParameterTree) else str(value)
            if path is None:
                path=value.path() if isinstance(value,ParameterTree) else string_to_path(str(value))
            #self.string=string
            self.path=path
            
    @classmethod
    def node_value(cls,node):
        return node.value if isinstance(node,cls.Entry) else node
    
    def __init__(self,_path=None,**kwargs):
        Tree.__init__(self,**kwargs)
        self._path=_path
        #self._string=_string
        
    def to_dict(self):
        def value_to_dict(value):
            if isinstance(value,self.Entry):
                return value_to_dict(value.value)
            elif isinstance(value,ParameterTree):
                return value.to_dict()
            else:
                return value
        return {key:value_to_dict(value) for key,value in self.items()}
       
    def path(self):
        """Return path representation of a ParameterTree.
        
        The path representation is intended to be concise, even at the expense
        of clarity, because of path length restriction of approx. 256 characters
        on Windows."""
        if self._path is not None:
            return self._path
        def get_path(key):
            child=self[key]
            if isinstance(child,ParameterTree):
                return child.path()
                # Used to wrap in brackets, but when I added Windows compatibility
                # I needed to make the paths more concise. Could add as an option
                # path=child.path()
                # if len(path)>0:
                #     return key+'('+path+')'
                # else:
                #     return ''
            elif isinstance(child,self.Entry):
                return child.path
            else:
                path=key
                value=string_to_path(str(child))
                if not (key[-1].isdigit() ^ value[0].isdigit()):
                    path+='='
                path+=value
                return path
        strings=[get_path(key) for key in sorted(self.keys())]
        strings=[string for string in strings if string != '']
        return join_with_underscores(*strings) #'_'.join(string for string in strings if string != '')
    
    def string(self):
        # if self._string is not None:
        #     return self._string
        def get_string(object):
            if isinstance(object,ParameterTree):
                return object.string()
            else:
                return str(object)
                
        def get_child_string(key):
            child=self[key]
            if isinstance(child,self.Entry):
                return get_string(child.value)
            else:
                child_string=get_string(child)
                if len(child_string)==0:
                    return ''
                return key+'('+child_string+')'
                
        #     elif isinstance(child,self.Entry):
        #         return get_string(child.value)
        #         
        #     child=self[key]
        #     if isinstance(child,ParameterTree):
        #         child_string=child.string()
        #         if len(child_string)==0:
        #             return ''
        #         return key+'('+child_string+')'
        #     else:
        #         if isinstance(child,self.Entry):
        #             child_string=get_string(child.value)
        #         else:
        #             child_string=child
        #         return key+'='+str(child_string)
        #     
        #     
        # def get_string(key):
        #     child=self[key]
        #     if isinstance(child,ParameterTree):
        #         child_string=child.string()
        #         if len(child_string)==0:
        #             return ''
        #         return key+'('+child_string+')'
        #     else:
        #         if isinstance(child,self.Entry):
        #             child_string=get_string(child.value)
        #         else:
        #             child_string=child
        #         return key+'='+str(child_string)
        strings=[get_child_string(key) for key in sorted(self.keys())]
        return ', '.join(string for string in strings if string != '')

if __name__=="__main__":
    a=ParameterTree(x=1)
    a['w']=0
    a['p']['y']=2
    a['p']['z']=3
    a['name']=ParameterTree.Entry('fred smith!','fred smith')
    a['thingo']=ParameterTree.Entry(ParameterTree(x=2),'x2')
    a['thingo2']=ParameterTree.Entry(ParameterTree(x=2,y=3),'x2y3')
    print('a.string()=',a.string())
    print('a.path()=',a.path())
    b=ParameterTree()
    b['x']=1
    b['w']=-1
    b['p']['y']=2
    b['p']['z']=4
    b['thingo']=ParameterTree.Entry(ParameterTree(x=2),'x2')
    b['thingo2']=ParameterTree.Entry(ParameterTree(x=2,y=4),'x2y4')
    common,onlys=a.compare_to(b)
    #print('common: ',str(common))
    print('common.string()=',common.string())
    #print('onlys[0]: ',str(onlys[0]))    
    print('onlys[0].string()=',onlys[0].string())
    #print('onlys[1]: ',str(onlys[1]))    
    #print('path: ',a.path())
    #print('string: ',a.string())

"""Description system

Possible definitions of a 'description':

* A description is (parameter name string->value description string) mapping. 
No! Want it to have an order. Also want it to have structure for easier manipulation

* A description is a list of tuples of (parameter name string, x) where x
is either a string or description. The reason for a list is to impose a sensible order.
Comparison of descriptions: perhaps better expressed as in recursive/tree language

* A description is a tree, each node a string. Leaves are parameter values.
Compare(nodes n1, n2):
"""
"""
def tree():
  return defaultdict(tree)
def compare_trees(node1,node2): 
  if node1==node2:
    return node1,None,None
  elif isinstance(node1,dict) and isinstance(node2,dict):
    common={}
    only1={}
    only2={}
    for key in node1.keys() | node2.keys():
      if key in node1 and key in node2:
        child1=node1[key]
        child2=node2[key]
        if child1==child2:
          common[key]=child1
        else:
          only1[key]=child1
          only2[key]=child2
      elif key in node1:
        only1[key]=node1[key]
      elif key in node2:
        only2[key]=node2[key]
    return common,only1,only2
  else:
    return None,node1,node2
"""
            
