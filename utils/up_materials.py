import bpy
import mathutils
from .up_os import import_node_tree

bl_version = bpy.app.version

def up_blendmat_node_group(mat, converted_mats, mixer_groups, bg_color):
    converted_mats.reverse()
    mixer_groups.reverse()
    if not(mat or orginal_mat):
        return none
        
    mat.use_nodes = True
    up_blendmat = mat.node_tree

    #start with a clean node tree
    for node in up_blendmat.nodes:
        up_blendmat.nodes.remove(node)
    
    material_output = up_blendmat.nodes.new("ShaderNodeOutputMaterial")
    material_output.name = "Material Output"
    material_output.is_active_output = True
    material_output.target = 'ALL'   
    
    base_shader = up_blendmat.nodes.new("ShaderNodeBsdfDiffuse")
    
    _vertical_height = 200
    
    base_shader.location = (-220, -200)
    
    loop_counter = 0
    prev_mixer_node = mixer_groups[0]
    material_output_y_offset = 0
    #loop_clipper = 2
    
    for _mixer in mixer_groups:
        # Skip the first two loops, because we already added those groups >:(
        # if loop_clipper > 0:
            # loop_clipper -= 1
            # continue
        
        # Create the new nodes: mixer, and group
        mixer_node = up_blendmat.nodes.new("ShaderNodeGroup")
        mixer_node.node_tree = _mixer
        
        #initialize up_blendmat links
        if loop_counter == 0:
            up_blendmat.links.new(base_shader.outputs[0], mixer_node.inputs[1])
            # up_blendmat.links.new(base_shader.outputs[1], mixer_node.inputs[3])
        
        group_a = up_blendmat.nodes.new("ShaderNodeGroup")
        group_a.node_tree = converted_mats[loop_counter]
        group_a.name = converted_mats[loop_counter].name
        mixer_node.location = (120, _vertical_height*loop_counter)
        group_a.location = (-220.0, _vertical_height*loop_counter)

        # Connect groups to mixers
        up_blendmat.links.new(group_a.outputs[0], mixer_node.inputs[0])
        if len(group_a.outputs) != 1: # Sometimes people are too lazy to use displacement
            up_blendmat.links.new(group_a.outputs[1], mixer_node.inputs[2]) 
        
        # Connect mixers to mixers >:D
        if loop_counter != 0:
            up_blendmat.links.new(prev_mixer_node.outputs[0], mixer_node.inputs[1])
            up_blendmat.links.new(prev_mixer_node.outputs[1], mixer_node.inputs[3])
        
        material_output_y_offset = _vertical_height*loop_counter
        
        prev_mixer_node = mixer_node   
        loop_counter += 1
        
    #group.Shader -> material_output.Surface
    up_blendmat.links.new(mixer_node.outputs[0], material_output.inputs[0])
    up_blendmat.links.new(mixer_node.outputs[1], material_output.inputs[2])
    
    material_output.location = (350, material_output_y_offset)
    base_shader.inputs[0].default_value = (*bg_color, 1)
    
    return up_blendmat

###########################################################

# def material_to_group(mat, group_name):
    # new_mat = mat.copy()
    # new_mat.name = "_temp_mat"
    # new_mat.use_nodes = True
    
    # node_tree = new_mat.node_tree
    # nodes = node_tree.nodes
    
    # area = next(area for area in bpy.context.screen.areas if area.type == 'NODE_EDITOR')
    # with bpy.context.temp_override(area=area, region=area.regions[-1], space=area.spaces.active):
        # node_tree.nodes.active = nodes[0] 
        # for node in nodes:
            # node.select = True
        # bpy.ops.node.group_make()
    
    # group_node = node_tree.nodes.active
    # group_node.node_tree.name = "YourGroupName"

    # # Remove the temporary material
    # bpy.data.materials.remove(new_mat)
    
# def material_to_group(mat, obj_name):
    # if not mat.node_tree:
        # return None

    # # Create new node group
    # group_name = f"_up_{obj_name} - {mat.name}"
    # #group = mat.node_tree.nodes.new('ShaderNodeGroup') #bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
  # # 1. Create an empty node group to register it in bpy.data
    # node_group = bpy.data.node_groups.new(name=group_name, type='ShaderNodeTree')

    # # 2. Assign that group to a ShaderNodeGroup in a material (optional visual feedback)
    # group_node = mat.node_tree.nodes.new('ShaderNodeGroup')
    # group_node.node_tree = node_group

    # # 3. Copy the source material's node tree
    # copied_tree = mat.node_tree.copy()

    # # 4. Replace the placeholder node_group's content with the copied one
    # # Since node groups don’t support .copy() overwrite, you must:
    # # - Delete all nodes in the placeholder
    # # - Paste the copied nodes/links manually

    # # Clear the new group
    # for node in node_group.nodes:
        # node_group.nodes.remove(node)

    # # Copy nodes from copied_tree to node_group
    # node_map = {}
    # for node in copied_tree.nodes:
        # new_node = node_group.nodes.new(node.bl_idname)
        # new_node.location = node.location
        # new_node.label = node.label
        # new_node.name = node.name
        # new_node.width = node.width
        # new_node.mute = node.mute
        # new_node.hide = node.hide
        # new_node.show_options = node.show_options

        # # Copy input default values
        # for i, input in enumerate(node.inputs):
            # if input.enabled and hasattr(input, 'default_value'):
                # if i < len(new_node.inputs):
                    # new_input = new_node.inputs[i]
                    # try:
                        # new_input.default_value = input.default_value
                    # except Exception as e:
                        # print(f"⚠️ Input {i} of '{new_node.name}' failed: {e}")

        # node_map[node] = new_node

    # # Recreate links
    # for link in copied_tree.links:
        # from_node = node_map[link.from_node]
        # to_node = node_map[link.to_node]
        # node_group.links.new(
            # from_node.outputs[link.from_socket.name],
            # to_node.inputs[link.to_socket.name]
        # )

    # return copied_tree

def material_to_group(original_mat, obj_name):

    if not original_mat.node_tree:
        return None

    # Create new node group
    group_name = f"_up_{obj_name} - {original_mat.name}"
    group = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    group_nodes = group.nodes
    group_links = group.links

    # Create Group Output node
    group_output_node = group_nodes.new('NodeGroupOutput')
    group_output_node.location = (300, 0)
    
    # Track original nodes and links
    original_nodes = original_mat.node_tree.nodes
    original_links = original_mat.node_tree.links
    original_output_node = next((n for n in original_nodes if n.type == 'OUTPUT_MATERIAL'), None)

    if not original_output_node:
        return group

    node_map = {}
    # This is a bit of a yucky scenario.  We have to copy over all the original node's properties.  (e.g. transforms on a vector mapping node)
    for node in original_nodes:
        if node == original_output_node:
            continue

        # Create the new node
        new_node = group_nodes.new(node.bl_idname)
        node_map[node] = new_node

        # Copy simple attributes
        new_node.location = node.location
        new_node.name = node.name
        new_node.label = node.label

        # Dynamically copy all properties
        for prop in node.bl_rna.properties:
            prop_name = prop.identifier
            
            # Skip read-only properties and already-copied attributes
            if prop.is_readonly or prop_name in {"name", "label", "location"}:
                continue

            # Ensure both nodes have the property
            if hasattr(node, prop_name) and hasattr(new_node, prop_name):
                try:
                    value = getattr(node, prop_name)

                    # Handle special Blender types
                    if isinstance(value, bpy.types.Image):  # Copy images (Texture nodes)
                        setattr(new_node, prop_name, value)
                    
                    elif isinstance(value, bpy.types.NodeTree):  # Copy node groups
                        setattr(new_node, prop_name, value)
                    
                    elif hasattr(value, "to_tuple"):  # Handle Vectors, Colors, Matrices
                        setattr(new_node, prop_name, value.to_tuple())
                    
                    elif isinstance(value, (int, float, bool, str)):  # Handle standard types
                        setattr(new_node, prop_name, value)

                except (AttributeError, TypeError):
                    pass

        # Copy input socket default values
        for input_socket, new_input_socket in zip(node.inputs, new_node.inputs):
            if input_socket.type in {'VALUE', 'VECTOR', 'RGBA'}:
                try:
                    value = input_socket.default_value

                    # Fix RGBA sockets that are missing alpha
                    try:
                        if input_socket.type == 'RGBA' and len(value) == 3:
                            value = (*value, 1.0)
                    except TypeError:
                        pass  # In case value doesn't support len()
                    print(new_input_socket.name)
                    new_input_socket.default_value = value
                except (AttributeError, TypeError, ValueError):
                    continue
    for link in original_links:
        if link.to_node == original_output_node or link.from_node == original_output_node:
            continue

        from_node = node_map.get(link.from_node)
        to_node = node_map.get(link.to_node)
        
        if from_node and to_node:
            from_socket = next((s for s in from_node.outputs if s.name == link.from_socket.name), None)
            to_socket = next((s for s in to_node.inputs if s.name == link.to_socket.name), None)
            
            if from_socket and to_socket:
                group_links.new(from_socket, to_socket)

    # Handle connections to the original output node
    for link in original_links:
        if link.to_node == original_output_node:
            socket_name = link.to_socket.name
            original_from_socket = link.from_socket
            group_from_node = node_map.get(link.from_node)

            if group_from_node:
                socket_type = link.to_socket.bl_idname

                # Check for existing output socket
                existing_socket = None
                for item in group.interface.items_tree:
                    if (item.item_type == 'SOCKET' and 
                        item.in_out == 'OUTPUT' and 
                        item.name == socket_name):
                        existing_socket = item
                        break

                # Create new socket if needed
                if not existing_socket:
                    group.interface.new_socket(
                        name=socket_name,
                        in_out='OUTPUT',
                        socket_type=socket_type
                    )

                # Find the new socket in Group Output node inputs
                group_from_socket = next(
                    (s for s in group_from_node.outputs if s.name == original_from_socket.name),
                    None
                )
                
                if group_from_socket:
                    # Connect to the corresponding Group Output input
                    output_socket = group_output_node.inputs.get(socket_name)
                    if output_socket:
                        group_links.new(group_from_socket, output_socket)

    return group
###########################################################
    
def up_mixer_node_group(name: str, istexture: bool, attr_name: str, uv_name: str, image_tex, mask_src, self):
    
    # Retreive Mixer node tree
    if name in bpy.data.node_groups:
        _up_mixer = bpy.data.node_groups[name]
    else:
        _up_mixer = import_node_tree('up_mixer.blend', 'up_mixer_preset_default', name)
    
    # Reference common nodes
    src_img_node  = _up_mixer.nodes['src_image']
    uv_map_node = _up_mixer.nodes['uv_map']
    vcol_node = _up_mixer.nodes['src_vcol']    
    up_mask_fx = _up_mixer.nodes['ngroup_up_mask_fx']   
    mask_input = _up_mixer.nodes["mask_input"] # Reroute that sources are connected to
    
    
    # Connect source node to mask_input
    if mask_src == "PAINT":
        if istexture:
            image_tex = bpy.data.images[attr_name]
            if image_tex:
                src_img_node.image = image_tex
                uv_map_node.uv_map = uv_name
            _up_mixer.links.new(src_img_node.outputs[0], mask_input.inputs[0])        
        else: 
            vcol_node.layer_name = attr_name
            _up_mixer.links.new(vcol_node.outputs[0], mask_input.inputs[0])
    
    elif mask_src == "AO":
        if "src_ao" in _up_mixer.nodes:
            _up_mixer.links.new(_up_mixer.nodes["src_ao"].outputs[0], mask_input.inputs[0])
        
    elif mask_src == "NOISE":
        if "src_noise" in _up_mixer.nodes:
            _up_mixer.links.new(_up_mixer.nodes["src_noise"].outputs[0], mask_input.inputs[0])
    
    
    # Warn user if a source isn't connected properly
    if len(mask_input.inputs[0].links) < 1: 
        self.report('WARNING', 'Thou hath tampereth with the mixer node group!')
        
    return _up_mixer
    
###################################################################

def _up_mask_fx_node_group():
    if "_up_mask_fx" in bpy.data.node_groups:
        return bpy.data.node_groups["_up_mask_fx"]
    else:
        import_node_tree('up_mixer.blend', '_up_mask_fx', '_up_mask_fx')    
        return _up_mask_fx

