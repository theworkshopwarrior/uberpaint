import bpy
import os

def import_node_tree(filename, node_tree_name, new_name, subfolder=""):   
    if new_name in bpy.data.node_groups:
        return bpy.data.node_groups[new_name]
        
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    
    blend_path = None
    if len(subfolder) > 0:
        blend_path = os.path.join(addon_dir, subfolder, filename)
    else:
        blend_path = os.path.join(addon_dir, filename)
        print('n sub')
        
    blend_node_tree_path = os.path.join(blend_path, "NodeTree")
    
    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        if node_tree_name in data_from.node_groups:
            data_to.node_groups = [node_tree_name]
        else:
            return None

    # Rename the imported node group
    if data_to.node_groups:
        node_group = data_to.node_groups[0]
        node_group.name = new_name
        return node_group
    else:
        return None