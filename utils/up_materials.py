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
        if len(group_a.outputs) > 0:
            up_blendmat.links.new(group_a.outputs[0], mixer_node.inputs[0])
            if len(group_a.outputs) > 1: # Sometimes people are too lazy to use displacement
                up_blendmat.links.new(group_a.outputs[1], mixer_node.inputs[2]) 
        else:
            raise ValueError("Source materials must have material outputs.")
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

def create_dummy_material(original_mat):
    dummy_name = f"TEMP_{original_mat.name}"
    if dummy_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[dummy_name])
    
    dummy_mat = original_mat.copy()
    dummy_mat.name = dummy_name
    return dummy_mat

def material_to_group(mat, group_name):
    if not mat.node_tree:
        return None
        
    # Ensure we have a valid context
    if not bpy.context.window:
        # Try to get a valid window
        for window in bpy.context.window_manager.windows:
            if window.screen:
                bpy.context.window = window
                break
        else:
            raise Exception("No valid window context found")

    dummy_mat = create_dummy_material(mat)
    tree = dummy_mat.node_tree
    
    group_name = str(f"_up_{group_name} - {mat.name}")
    
    # Clean up if group already exists
    if group_name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])

    # Select non-output nodes
    nodes_to_group = [n for n in tree.nodes if not isinstance(n, bpy.types.ShaderNodeOutputMaterial)]
    if not nodes_to_group:
        bpy.data.materials.remove(dummy_mat)
        raise Exception("Needs at least 1 node to generate.")

    for node in tree.nodes:
        node.select = False
    for node in nodes_to_group:
        node.select = True
    tree.nodes.active = nodes_to_group[0]

    # Store original area type to restore later
    original_area_type = None
    if bpy.context.area:
        original_area_type = bpy.context.area.type

    # Find or create node editor area
    screen = bpy.context.window.screen
    area = next((a for a in screen.areas if a.type == 'NODE_EDITOR'), None)
    
    is_new_area = False
    if not area:
        # Temporarily change an area to NODE_EDITOR if none exists
        area = screen.areas[0]
        original_area_type = area.type
        area.type = 'NODE_EDITOR'
        is_new_area = True

    try:
        # Configure node editor
        space = area.spaces[0]
        space.tree_type = 'ShaderNodeTree'
        space.shader_type = 'OBJECT'
        old_tree = space.node_tree
        space.pin = True
        space.node_tree = tree

        # Force UI update
        bpy.ops.wm.redraw_timer(type='DRAW_SWAP', iterations=1)
            
        # Build override context
        override = {
            'window': bpy.context.window,
            'screen': screen,
            'area': area,
            'region': next((r for r in area.regions if r.type == 'WINDOW'), None),
            'space_data': space,
            'edit_tree': tree,
            'node_tree': tree,
        }

        # Perform grouping
        with bpy.context.temp_override(**override):
            bpy.ops.node.group_make()
        
        # Clean up
        space.pin = False
        space.node_tree = old_tree
        
        # Get the created group
        sel_nodes = [x for x in tree.nodes if x.select]
        if not sel_nodes:
            raise Exception("Group creation failed - no selected nodes after operation")
            
        ngroup_node = sel_nodes[0]
        ngroup_node.node_tree.name = group_name
        node_group = bpy.data.node_groups.get(group_name)
        
        if not node_group:
            raise Exception("Failed to create node group")
        
        # Add keys to group
        node_group['_up_mat'] = mat.name
        node_group['_up_type'] = 'MATERIAL'

        return node_group

    finally:
        # Clean up dummy material
        if dummy_mat.name in bpy.data.materials:
            bpy.data.materials.remove(dummy_mat)

        # Restore original area type if we changed it
        if is_new_area and area and original_area_type:
            area.type = original_area_type

###########################################################

def create_paint_layer(layer, obj):
    name = f"{layer.name} Paint ({obj.name}) {layer.id}" 
    
    if name in bpy.data.node_groups:
        group = bpy.data.node_groups[name]
    else:
        group = import_node_tree('up_mixer.blend', '_up_paint_layer', name)
    
    if obj.uberpaint.mask_type == 'TEXTURE':
        group.nodes['base_color'].image = layer.image_texture
        group.nodes['base_color'].interpolation = 'Cubic'
        group.nodes['uv_map'].uv_map = '_upm_paintUVs'
        group.links.new(group.nodes['base_color'].outputs[0], group.nodes['col_in'].inputs[0])
    if obj.uberpaint.mask_type == 'VERTEX':
        group.nodes['col_attr'].layer_name = layer.color_attr
        group.links.new(group.nodes['col_attr'].outputs[0], group.nodes['col_in'].inputs[0])
 
    if not group:
        raise Exception("Failed to create node group")
    
    # Add keys to group
    group['_up_type'] = 'PAINT'
    layer.paint_group = group
    
    return group
            
###########################################################
    
def up_mixer_node_group(obj, layer, name, uv_name, self):
    image_tex = layer.image_texture
    mask_src = layer.mask_source
    layer_type = layer.type
    layer_id = layer.id
    attr_name = layer.color_attr    
    istexture = (obj.uberpaint.mask_type == 'TEXTURE')
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
    
    # Remove unnecasary up_mask_fx groups
    up_mask_fx.node_tree = bpy.data.node_groups['_up_mask_fx']
    for grp in bpy.data.node_groups:
        if grp.name.startswith('_up_mask_fx') and grp.name != '_up_mask_fx':
            bpy.data.node_groups.remove(grp)
        
    # Connect source node to mask_input
    if mask_src == "PAINT":
        print('lalala paint')
        if istexture:
            image_tex = bpy.data.images[attr_name]
            if image_tex:
                src_img_node.image = image_tex
                src_img_node.interpolation = 'Cubic'
                uv_map_node.uv_map = uv_name
                _up_mixer.links.new(src_img_node.outputs[0], mask_input.inputs[0])        
                if layer_type == 'PAINT':
                    _up_mixer.links.new(src_img_node.outputs[1], mask_input.inputs[0]) 
        else: 
            vcol_node.layer_name = attr_name
            _up_mixer.links.new(vcol_node.outputs[0], mask_input.inputs[0])
            if layer_type == 'PAINT':
                _up_mixer.links.new(vcol_node.outputs[0], mask_input.inputs[0]) 
            
    elif mask_src == "AO":
        if "src_ao" in _up_mixer.nodes:
            _up_mixer.links.new(_up_mixer.nodes["src_ao"].outputs[0], mask_input.inputs[0])
        
    elif mask_src == "NOISE":
        if "src_noise" in _up_mixer.nodes:
            _up_mixer.links.new(_up_mixer.nodes["src_noise"].outputs[0], mask_input.inputs[0])
    
    # # Warn user if a source isn't connected properly
    # if len(mask_input.inputs[0].links) < 1: 
        # self.report('WARNING', 'Thou hath tampereth with the mixer node group!')
        
    _up_mixer['_up_type'] = "MIXER"
    _up_mixer['_up_id'] = layer_id
    _up_mixer['_up_obj'] = obj.name
    
    return _up_mixer
    
###################################################################

def _up_mask_fx_node_group():
    if '_up_mask_fx' in bpy.data.node_groups:
        return bpy.data.node_groups["_up_mask_fx"]
    else:
        import_node_tree('up_mixer.blend', '_up_mask_fx', '_up_mask_fx')    
        return _up_mask_fx

