bl_info = {
    "name": "UberPaint Beta",
    "description": "Quickly paint PBR materials using vertex colors or textures",
    "location": "N-Panel",
    "author": "Forest Stook",
    "version": (0, 9, 0),
    "blender": (4, 4, 0),
    "category": "Material",
    "warning": "UberPaint is still in development and may have bugs. Report issues to iotbot2010@gmail.com",
}

links = {"Discord" : 'https://discord.gg/NQ68E2y26P',
         "Gumroad" : "https://theworkshopwarrior.gumroad.com/",
         }
         
#_TODO:_
# Fix image textures
# Clean up unneccesary pointers
# Remove references to pointers upon object deletion

# _DONE:_
#--- 0.9:
# Displacement offset
# Renamable layers
# UI improvements
# Fix node group removal
# Check image texture functionality
# Finish replacing references with new naming, (e.g.) scene.target with scene.uberpaint.target
# Add list item at top
# Don't show invalid objects or materials in selectors
# Alert user that vertex color paint layers suck
# Set white/black paint colors by default in image texture mode
# Add alert and cancel on empty material entries
# Work with duplicate material entries
# Fix image/attribute when changing material
# Allow paint layers to work on generation
# Displacement blending textures are automatically added

# _IMPEDED:_
# Don't open up popup if already up?

import bpy, mathutils, textwrap

from bpy import context
from bl_ui.generic_ui_list import draw_ui_list
from random import uniform

from bpy.props import (IntProperty,
                       BoolProperty,
                       StringProperty,
                       CollectionProperty,
                       PointerProperty)
from bpy.types import (Operator,
                       Panel,
                       PropertyGroup,
                       UIList)
                       
from .utils.insult_engine import goofy_insult
from .utils import up_materials

# Reloading - dev only #####################
from importlib import reload
reload(up_materials)
# #########################################

from .utils.up_materials import (
    up_mixer_node_group,
    up_blendmat_node_group, 
    material_to_group,
    create_paint_layer
)

# --- SETTINGS ---
up_version = ".".join(map(str, bl_info["version"][:2]))
up_info = "Alpha"
bl_version = bpy.app.version
#---------------


###########################################################
# Functions
###########################################################

def get_layer_icon(index):
    layer_type = bpy.context.scene.uberpaint.target.uberpaint.layers[index].type
    icons = {
        "MATERIAL": "MATERIAL",
        "PAINT": "BRUSHES_ALL",
        "GENERATOR": "TEXTURE_DATA",
    }
    return icons.get(layer_type, "nothing")

def update_blendmat(self, context):
    # Do only if already has a blend material
    if bpy.context.scene.uberpaint.target.uberpaint.has_mask:  
        bpy.ops.up.generate_material(isupdate=True)

def up_draw_socket(layout, context, node, socket_name, label=""):
    row = layout.row()
    socket = node.inputs[socket_name]
    row_label = label if label != "" else socket.name
    row.label(text=row_label)
    socket.draw(context, row, node, socket.name)
   
def get_active_layer(context):
    scene = context.scene
    target = scene.uberpaint.target 
    if hasattr(target.uberpaint, "layers") and len(target.uberpaint.layers) > target.uberpaint.layer_index:
        return target.uberpaint.layers[target.uberpaint.layer_index]
    return None

def generate_id(layers):
    letters = ['a', 'b', 'c', 'x', 'f']
    id = str(int(uniform(1000, 9999))) + letters[int(uniform(0, len(letters)-1))]
    while any(layer.id == id for layer in layers):
        id = str(uniform(1000, 9999)) + letters[uniform(0, len(letters)-1)]     
    return id
    
def copy_layers(old, new):
    layers = old.uberpaint.layers
    for layer in layers:
        new_layer = new.uberpaint.layers.add()
        new_layer.id = generate_id(new.uberpaint.layers)    
        new_layer.name = layer.name
        new_layer.type = layer.type
        new_layer.material = layer.material
        new_layer.opacity = layer.opacity
        new_layer.mask_source = layer.mask_source

def mat_filter(self, material):
    if not material:
        return False
    
    if material.library:
        return False
    
    if material.is_grease_pencil:
        return False
    
    if hasattr(material, 'override_library') and material.override_library:
        return False
        
    if 'up_bmat' in material:
        return False
    
    return True

def obj_filter(self, object):
    if object.type != 'MESH':
        return False
    
    return True

def find_disp_texture(material):
    if not material or not material.use_nodes:
        return None

    node_tree = material.node_tree
    disp_textures = []

    displacement_node_types = {'DISPLACEMENT'}

    for node in node_tree.nodes:
        if node.type in displacement_node_types:
            for input in node.inputs:
                if input.is_linked:
                    linked_node = input.links[0].from_node
                    if linked_node.type == 'TEX_IMAGE' and linked_node.image:
                        disp_textures.append(linked_node.image)

    return disp_textures
    

###########################################################
# Classes
###########################################################

class UP_PT_MainPanel(bpy.types.Panel):
    bl_label = "UberPaint " + up_info + " V" + str(up_version)
    bl_idname = "UP_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'UberPaint'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.scene.uberpaint.target
        
        row = layout.row()
        row.prop_search(context.scene.uberpaint, "target", context.scene, "objects", text="Target Object")
        row.operator("up.set_target", text="", icon="MOD_LINEART")
        
        if obj:
            layers = obj.uberpaint.layers
            layout.label(text="Layers:")   
            
            row = layout.row()
            
            row.template_list("UP_UL_MaterialList", "", obj.uberpaint, "layers", obj.uberpaint, "layer_index")
            
            col = row.column(align=True)
            col.enabled = obj.mode == "OBJECT"
            
            col.operator("up.manage_layers", icon='ADD', text="").action = 'ADD'
            col.operator("up.manage_layers", icon='REMOVE', text="").action = 'REMOVE'
            #col.separator()
            #col.menu("MATERIAL_MT_context_menu", icon='DOWNARROW_HLT', text="")
            col.separator()
            col.operator("up.manage_layers", icon='TRIA_UP', text="").action = 'UP'
            col.operator("up.manage_layers", icon='TRIA_DOWN', text="").action = 'DOWN'
            
            if len(obj.uberpaint.layers) < 1:
                col.separator()
                row = col.row()
                row.enabled = (context.active_object != obj and context.active_object.uberpaint.has_mask)
                row.operator("up.copy_layers", icon='PASTEFLIPUP', text="")
            
            if not obj.uberpaint.has_mask:
                layout.label(text="Mask Target:")
                layout.prop(obj.uberpaint, "mask_type", text="")
            
            # Layer generation button
            row = layout.row()
            row.enabled = bpy.context.object.mode == "OBJECT"
            row.scale_y = 1.5
            
            # Vertex color paint layer warning
            if (not obj.uberpaint.has_mask) and obj.uberpaint.mask_type == 'VERTEX' and any(layer.type == 'PAINT' for layer in obj.uberpaint.layers):
                info=row.operator('wm.info', text ="", icon="ERROR")
                info.message1="Paint Layer"
                info.message2="Paint layers may have unexpected results when in Vertex Painting mode. Switch to texture painting for better results."
            
            if scene.uberpaint.target.uberpaint.has_mask:
                row.operator("up.generate_material", text="Update Blend Material", icon="FILE_REFRESH").isupdate = True
            else:
                row.operator("up.generate_material", text="Generate Blend Material", icon="SHADERFX").isupdate = False
                _settings_menu = row.operator("wm.settingsmenu", text="", icon="PREFERENCES")
                #_settings_menu.enabled = not(scene.uberpaint.target.uberpaint.has_mask)
            #------------------------------------
            
            # Layer deletion button
            row = layout.row()
            row.enabled = scene.uberpaint.target.uberpaint.has_mask and bpy.context.object.mode == "OBJECT"
            row.operator("up.remove_material", text="Remove Blend Material", icon="TRASH")
            
            layout.separator()
            if scene.uberpaint.target.uberpaint.has_mask:
                row = layout.row()
                row.enabled = (bpy.context.object.mode == 'OBJECT')
                row.prop(obj.uberpaint, "displacement_mode", text="Displacement Mode")

    
class UP_PT_PropsPanel(bpy.types.Panel):
    bl_label = ""
    bl_idname = "UP_PT_PropsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'UberPaint'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.scene.uberpaint.target   
        
        if obj and obj.uberpaint.has_mask:
            active_layer = get_active_layer(context)  
            if active_layer:
                box = layout.box()
                box.enabled = (bpy.context.object.mode == 'OBJECT')
                mgroup = active_layer.mixer_group
                box.prop(active_layer, 'name', text="Name")
                box.prop(active_layer, 'type')
                
                if active_layer.type == 'MATERIAL' and mgroup:            
                    box.prop(active_layer, "material", text="Source Material")
                    
                    box = layout.box()
                    box.enabled = (bpy.context.object.mode == 'OBJECT')
                    
                    mask_src = active_layer.mask_source
                    box.prop(active_layer, 'mask_source')
                    
                    if mask_src == "AO" and mgroup.nodes.get('src_ao'):
                        box.template_node_inputs(mgroup.nodes['src_ao'])
                    if mask_src == "NOISE" and mgroup.nodes.get('src_noise'):
                        box.template_node_inputs(mgroup.nodes['src_noise'])
                    
                    box.label(text="Mask Adjustments")      
                    row = box.row()
                    opacity_node = mgroup.nodes["opacity"]
                    socket = opacity_node.inputs[0]
                    row.label(text="Opacity")
                    socket.draw(context, row, opacity_node, socket.name) # Opacity Slider
                    box.label(text="Mask Controls:")
                    mgroup.nodes["color_adjustments"].draw_buttons(context, box) # Color Ramp                
                    
                    box.separator()
                    
                    box.label(text="Displacement Blending")
                    fx_node = mgroup.nodes["ngroup_up_mask_fx"]
                    disp_node = mgroup.nodes["disp_blending_tex"]
                    
                    disp_node.draw_buttons(context, box)
                    for input_socket in fx_node.inputs:
                        if not input_socket.is_linked:
                            box.prop(input_socket, "default_value", text=input_socket.name)
                            
                    box.separator()
                    
                    up_draw_socket(box, context, mgroup.nodes["disp_offset"], 'Scale', "Displacement Offset:")
                    up_draw_socket(box, context, mgroup.nodes["disp_height"], 'Scale', "Displacement Height:")
                    
                elif active_layer.type == 'PAINT': 
                    box = layout.box()
                    box.enabled = (bpy.context.object.mode == 'OBJECT')
                    
                    row = box.row()
                    
                    opacity_node = mgroup.nodes["opacity"]
                    socket = opacity_node.inputs[0]
                    row.label(text="Opacity")
                    socket.draw(context, row, opacity_node, socket.name) # Opacity Slider
                    
                    box = layout.box()
                    box.label(text = "Paint Material Properties")
                    layer = active_layer
                    painter_name = f"{layer.name} Paint ({obj.name}) {layer.id}" 
                    paint_group = obj.uberpaint.blend_mat.node_tree.nodes[painter_name]
                    for input_socket in paint_group.inputs:
                        if not input_socket.is_linked:
                            box.prop(input_socket, "default_value", text=input_socket.name)
                    box.label(text="Normal Map")
                    paint_group.node_tree.nodes["normal_map"].draw_buttons(context, box)
                    mgroup.nodes["color_adjustments"].draw_buttons(context, box)
                    
                    box = layout.box()
                    up_draw_socket(box, context, mgroup.nodes["disp_offset"], 'Scale', "Displacement Offset")
                    up_draw_socket(box, context, mgroup.nodes["disp_height"], 'Scale', "Displacement Height")
            else:
                box = layout.box()
                box.label(text="Please add at least one layer.  "+goofy_insult(), icon="ERROR")
        else:
            box = layout.box()
            box.label(text="Please generate a blend material.  "+goofy_insult(), icon="ERROR")
    
    def draw_header(self, context):
        if context.scene.uberpaint.target and context.scene.uberpaint.target.uberpaint.has_mask and context.scene.uberpaint.target.uberpaint.layers != None:
           active_layer = get_active_layer(context) 
           row = self.layout.row()       
           row.label(text=f"Layer Properties - {active_layer.name}")
        else:
           row = self.layout.row()       
           row.label(text="Layer Properties")


class UP_PT_PreferencesPanel(bpy.types.AddonPreferences):
    bl_idname = __name__
    
    bg_color: bpy.props.FloatVectorProperty(name="Base Layer Color", subtype='COLOR', size=3, default=[0.1, 1, 0.0])
    use_goofy_insults: bpy.props.BoolProperty(name="Use Goofy Insults", default=True)
    
    def draw(self, context):
        layout = self.layout
        #layout.label(text='Default Layer Color')
        row = layout.row()
        row.prop(self, 'bg_color')
        
        row = layout.row()
        row.prop(self, 'use_goofy_insults')
        if self.use_goofy_insults:
            row.label(text="E.G. " + goofy_insult())
        else:
            row.label(text="E.G. " + "404 brain not found.")
            
        layout.separator()
        
        box = layout.box()
        box.label(text="If you've found this addon useful, please consider donating.", icon="FUND")
        row = box.row()
        op = row.operator('wm.url_open', text="My Gumroad", icon="URL")
        op.url = links.get("Gumroad")       
        op = row.operator('wm.url_open', text="Discord Server", icon="URL")
        op.url = links.get("Discord")


class UP_PT_ShaderPanel(bpy.types.Panel):
    bl_label = "UberPaint Node Editor Utilities"
    bl_idname = "UP_PT_ShaderPanel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'UberPaint'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.scene.uberpaint.target
        mat = obj.active_material
        materials = [entry.material for entry in obj.uberpaint.layers if entry.material]  
        
        if obj and bl_version > (4, 1, 0):
            row = layout.row()
            row.scale_y = 3
            row.enabled = obj.uberpaint.has_mask and (mat in materials)
            row.alert = True
            row.operator("up.rebuild_src", text=f"Update this Group", icon="FILE_REFRESH", icon_value=656, emboss=True)


class UP_PT_SupportPanel(bpy.types.Panel):
    bl_label = "Support"
    bl_idname = "UP_PT_SupportPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'UberPaint'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.label(text="Thank you for using UberPaint!")
        row = box.row()
        op = row.operator('wm.url_open', text="My Gumroad", icon="URL")
        op.url = links.get("Gumroad")       
        op = row.operator('wm.url_open', text="Discord Server", icon="URL")
        op.url = links.get("Discord")


class WM_OT_InfoBox(bpy.types.Operator):
    """What is this?"""
    bl_idname = "wm.info"
    bl_label = "Information"
    
    message1: bpy.props.StringProperty(default="Info")
    message2: bpy.props.StringProperty(default="There should really be something here...")
    icon: bpy.props.StringProperty(default="QUESTION")
    
    def execute(self, context):
        return {'FINISHED'}
 
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width = 400)
 
    def draw(self, context):
        layout = self.layout
        
        #layout.label(icon=str(self.icon), text=str(self.message1))
        
        # Wrapping to avoid overflow       
        textTowrap = self.message2    
        wrapp = textwrap.TextWrapper(width=60)    
        wList = wrapp.wrap(text=textTowrap) 
        
        for text in wList: 
            row = layout.row(align = True)
            row.alignment = 'EXPAND'
            row.scale_y = 0.6
            row.label(text=text)


class UP_OT_GenerateMaterial(bpy.types.Operator):
    """Generate a blend material for the target object"""
    bl_idname = "up.generate_material"
    bl_label = "Generate Layer Material"
    
    isupdate: bpy.props.BoolProperty(False) # False for generation, true for updates
    
    def execute(self, context):
        wm = bpy.context.window_manager
        wm.progress_begin(0, 100)
        
        scene = context.scene
        obj = scene.uberpaint.target
        blend_mode = context.scene.uberpaint.target.uberpaint.mask_type
        materials = [entry.material for entry in scene.uberpaint.target.uberpaint.layers if entry.material]       
        mesh_dat = obj.data
            
        # Preliminary checks to avoid disaster
        if obj.type != "MESH":
            self.report({'WARNING'}, "Target object is not a mesh.  " + goofy_insult())
            return {'CANCELLED'}
        if len(materials) < 2:
            self.report({'WARNING'}, "Please select at least two materials.  " + goofy_insult())
            return {'CANCELLED'}
            
        all_materials = [entry.material for entry in scene.uberpaint.target.uberpaint.layers] 
        for layer in obj.uberpaint.layers or (obj.target.uberpaint.layer_index < len(obj.target.uberpaint.layers)):
            if layer.type == 'MATERIAL' and (not layer.material):
                self.report({'WARNING'}, "Please remove unused material slots!  " + goofy_insult())
                return {'CANCELLED'}            
            
        if self.isupdate == True: 
            bpy.ops.up.remove_material(isupdate=True)
            
        # Remove all material slots
        obj.data.materials.clear()
                
        # Select and activate target; This may be removed soon.         
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        
        # -----Create Blend Material-----
        blend_mat_name = obj.name + " Blend Mat"
        
        # Check if this object already has a material
        if any(mat and mat.name == blend_mat_name for mat in obj.data.materials):
            self.report({'WARNING'}, "This object already has a blend material.  " + goofy_insult())
            return {'CANCELLED'}
         
        mask_res = scene.uberpaint.texture_resolution
        # Ready to go?  Check if we're using an image or a vertex texture and add attributes accordingly.     
        obj_image_textures =[]
        obj_vgroups = []
        if blend_mode == "TEXTURE":
            if '_upm_paintUVs' not in obj.data.uv_layers:
                tex_UVs = obj.data.uv_layers.new(name="_upm_paintUVs")
                mesh_dat.uv_layers.active = mesh_dat.uv_layers["_upm_paintUVs"]
                obj.select_set(True)
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_mode(type="FACE")
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.03)
                bpy.ops.object.mode_set(mode='OBJECT')

            rep=0
            for layer in obj.uberpaint.layers:
                attr_name = f"_upm: {obj.name} - {layer.name} ({layer.id})"
                if not attr_name in bpy.data.images:
                    image_tex = bpy.data.images.new(attr_name, width=mask_res, height=mask_res)
                    
                    if rep == len(obj.uberpaint.layers)-1 and not self.isupdate:
                        image_tex.pixels = [1.0, 1.0, 1.0, 1.0] * (mask_res * mask_res)
                    else:
                        image_tex.pixels = [0.0, 0.0, 0.0, 0] * (mask_res * mask_res)
                    image_tex.pack()
                    obj_image_textures.append(image_tex)
                    
                    layer.image_texture = image_tex
                    layer.color_attr = attr_name
                    print("Added:" +attr_name)

                rep+=1
                          
        elif blend_mode == "VERTEX":           
            for layer in obj.uberpaint.layers:
                attr_name = f"_upm: {obj.name} - {layer.name} ({layer.id})"
                layer.color_attr = attr_name
            
            i = 0 
            ngroups = obj.data.vertex_colors
            valid_vcols = [vcol.name for vcol in ngroups if vcol.name.startswith('_upm: '+obj.name+" - ")]      
            vcols_to_add = {mat.color_attr for mat in obj.uberpaint.layers}

            for vcol in vcols_to_add:
                if (vcol not in valid_vcols):
                    avc = obj.data.vertex_colors.new(name=vcol)  
                    # Set vertex colors to black on all but bottom layer
                    for loop in mesh_dat.loops:
                        avc.data[loop.index].color = (0, 0, 0, 1.0) 
                if not self.isupdate:
                    if obj.uberpaint.layers[len(obj.uberpaint.layers)-1].color_attr == vcol:
                        avc = mesh_dat.vertex_colors[vcol]
                        for loop in mesh_dat.loops:
                            avc.data[loop.index].color = (1, 1, 1, 1.0)   
                i+=1
            
        wm.progress_update(50)
        
        ##############################################
        # This is where the magic happens.  Adding the node groups to the material
            
        #is_tex = True if blend_mode == "TEXTURE" else (False if blend_mode == "VERTEX" else None)
        rep=0      
        mixer_groups = []
        converted_mats = []
        prev_layers = {}
        for layer in obj.uberpaint.layers:     
            mixer_name = f"{layer.name} Mixer ({obj.name}) {layer.id}" 
            layer_mixer = up_mixer_node_group(obj, layer, mixer_name, "_upm_paintUVs", self)
            layer.mixer_group = layer_mixer
            mixer_groups.append(layer_mixer)
            
            layer_group = None
            if layer.type == 'MATERIAL':
                material_key = layer.material.name
                if material_key in prev_layers:
                    layer_group = prev_layers[material_key]
                else:
                    layer_group = material_to_group(layer.material, obj.name)
                    prev_layers[material_key] = layer_group
                    
            elif layer.type == 'PAINT':
                layer_group = create_paint_layer(layer, obj)
                
            layer_group['_up_obj'] = obj.name
            converted_mats.append(layer_group)
        
        blend_mat = bpy.data.materials.new(blend_mat_name)
        blend_mat.use_nodes = True
        print(converted_mats)
        if bl_version < (4, 1, 0):
            blend_mat.cycles.displacement_method = obj.uberpaint.displacement_mode
        else: 
            blend_mat.displacement_method = obj.uberpaint.displacement_mode
            
        bg_col = context.preferences.addons[__name__].preferences.bg_color
        up_blendmat_node_group(blend_mat, converted_mats, mixer_groups, bg_col)
            
            
        for layer in obj.uberpaint.layers:
            if layer.type == 'MATERIAL':
                if layer.mixer_group.nodes['disp_blending_tex'] and len(find_disp_texture(layer.material)) > 0:                
                    layer.mixer_group.nodes['disp_blending_tex'].image = find_disp_texture(layer.material)[-1] # Return last item
            
            
        scene.uberpaint.target.uberpaint.has_mask = True
        
        blend_mat['_up_bmat'] = True
        obj.data.materials.append(blend_mat)
        scene.uberpaint.target.uberpaint.blend_mat = blend_mat
        
        # Add all source materials so they can be previewed/easily edited
        for mat in materials:
            if mat:
                obj.data.materials.append(mat)  # Add material slot
                
        wm.progress_update(100)
        wm.progress_end()
        bpy.ops.ed.undo_push()    
        
        self.report({'INFO'}, "Material Created Successfully")        
        return {'FINISHED'}


class UP_OT_ManageLayers(bpy.types.Operator):
    """Reorder, add, or remove a layer"""
    bl_idname = "up.manage_layers"
    bl_label = "Manage Layer"
    action: bpy.props.EnumProperty(
        items=[
            ('ADD', "Add", "Add a new material"),
            ('REMOVE', "Remove", "Remove selected material"),
            ('UP', "Move Up", "Move material up"),
            ('DOWN', "Move Down", "Move material down")
        ]
    )

    def execute(self, context):
        scene = context.scene
        obj = scene.uberpaint.target
        layers = obj.uberpaint.layers
        layer_index = obj.uberpaint.layer_index

        if self.action == 'ADD':
            new_mat = layers.add()
            
            collection = layers 
            base_name = "Layer"
            new_name = base_name
            counter = 1
            # Find a unique name
            while any(item.name == new_name for item in layers):
                new_name = f"{base_name} {counter}"
                counter += 1
            
            new_mat.material = None
            new_mat.name = new_name       
            
            # Generate a new ID for each layer           
            new_mat.id = generate_id(layers)   
            
            obj.uberpaint.layer_index = len(layers) - 1
            layers.move(obj.uberpaint.layer_index, 0)
            obj.uberpaint.layer_index = 0
            
        elif self.action == 'REMOVE' and layer_index >= 0:
            layers.remove(layer_index)
            obj.uberpaint.layer_index  = max(0, layer_index - 1)
        elif self.action == 'UP' and layer_index > 0:
            layers.move(layer_index, layer_index - 1)
            obj.uberpaint.layer_index  -= 1
        elif self.action == 'DOWN' and layer_index < len(layers) - 1:
            layers.move(layer_index, layer_index + 1)
            obj.uberpaint.layer_index  += 1

        if scene.uberpaint.target.uberpaint.has_mask and self.action != 'ADD':
            if layer_index < len(layers):
                if layers[layer_index].material is not None:
                    bpy.ops.up.generate_material(isupdate=True)
        
        return {'FINISHED'}


class UP_OT_RebuildSourceGroup(bpy.types.Operator):
    """Refresh the current source material's node tree"""
    bl_idname = "up.rebuild_src"
    bl_label = "Rebuild Group"
    
    def execute(self, context): 
        scene = context.scene
        obj = scene.uberpaint.target
        # materials = [entry.material for entry in obj.uberpaint.layers if entry.material]    
        # mat_index = obj.active_material_index
        # blend_mat = obj.uberpaint.blend_mat
        screen = bpy.context.window.screen
        area = next((a for a in screen.areas if a.type == 'NODE_EDITOR'), None)
        space = area.spaces[0]
        
        old_material_index = obj.active_material_index  # Store the current material slot index
        old_material_name = obj.active_material.name   # Optional: For debugging/logging

        space.node_tree = bpy.data.materials[old_material_name].node_tree
        space.pin = True

        if scene.uberpaint.target.uberpaint.has_mask:
            bpy.ops.up.generate_material(isupdate=True)  # This may change the active material
            # Restore the originally selected material slot
            obj.active_material_index = old_material_index

        # Unpin current material (now the original one is active again)
        space.pin = False
              
        return {'FINISHED'}


class UP_OT_RemoveMaterial(bpy.types.Operator):
    """Remove and clean up the target object's blend materal"""
    bl_idname = "up.remove_material"
    bl_label = "Remove Blend Material"
    
    isupdate: bpy.props.BoolProperty(False) # False for full removal, true for updates
    
    def execute(self, context):
        scene = context.scene
        obj = bpy.context.scene.uberpaint.target
        blend_mode = context.scene.uberpaint.target.uberpaint.mask_type
        materials = [entry.material for entry in scene.uberpaint.target.uberpaint.layers if entry.material]
        isupdate = self.isupdate
        
        # Check if the target already has a blend mat
        if scene.uberpaint.target.uberpaint.has_mask == False:
            return {'CANCELLED'}
        
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        
        m = obj.uberpaint.blend_mat
        if not m:
            self.report({'WARNING'}, "We couldn't find the blend material. Did you delete it? Try regenerating.")
            scene.uberpaint.target.uberpaint.has_mask = False
            return {'CANCELLED'}
        
        bpy.data.materials.remove(m)
        bpy.ops.object.material_slot_remove()
        
        # Remove UVs :D
        if not(isupdate) and '_upm_paintUVs' in obj.data.uv_layers:
            uv_layer = obj.data.uv_layers['_upm_paintUVs']
            obj.data.uv_layers.remove(layer=uv_layer)
        
        # Remove Image Textures
        upm_images = [img for img in bpy.data.images if img.name.startswith("_upm: "+obj.name+" - ")]
        obj_texs = [entry.image_texture for entry in obj.uberpaint.layers if entry.image_texture] 
        if upm_images:
            if isupdate:
                for img in upm_images:
                    if not img.users:  # Check if the image has no real users
                        bpy.data.images.remove(img)  # Remove the image
            else:
                for img in bpy.data.images:
                    if img.name.startswith('_upm: '+obj.name+" - "):
                        bpy.data.images.remove(img)
        
        # # Remove Color Attributes :D
        vcol_layers = obj.data.vertex_colors
        vcols = [vcol for vcol in vcol_layers if vcol.name.startswith('_upm: '+obj.name+" - ")]      
        if hasattr(obj.data, "vertex_colors") and len(vcols)>0: # and obj.mask_type == "VERTEX":
            obj_clrs = [entry.color_attr for entry in obj.uberpaint.layers if entry.color_attr] 
            vcols = []
            for color_attr in obj_clrs:
                vcols.append(obj.data.vertex_colors[color_attr])
            vcols.reverse()
            
            vt_colors = obj.data.vertex_colors
            
            if isupdate:  
                rep = 0
                for vcol in vcols:
                    if vcol not in list(vt_colors):
                        vt_colors.remove(vcol)
                        rep+=1
            else:
                vcol_layers = obj.data.vertex_colors
                vcols = [vcol for vcol in vcol_layers if vcol.name.startswith('_upm: '+obj.name+" - ")]
                vcols.reverse() # Do this or else strange things happen
                for vcol in vcols:
                    vt_colors.remove(vcol)
                        
        # Remove node groups 
        print(f"UberPaint: Removing node groups for {obj.name}")
        
        # Clear PointerProperties
        if not isupdate:
            for layer in obj.uberpaint.layers:
                layer.mixer_group = None
                layer.paint_group = None
                #layer.material = None
                layer.image_texture = None
                layer.paint_group = None
                # obj.uberpaint.layers.remove(layer.index)
                
        for ngroup in bpy.data.node_groups:
            if '_up_obj' in ngroup:
                if ngroup['_up_obj'] == obj.name:
                    print('found a node group for obj'+str(ngroup['_up_obj']))
                    if '_up_type' in ngroup:
                        print('found a node group'+str(ngroup['_up_obj']))
                        if ngroup['_up_type'] == 'MIXER' or ngroup['_up_type'] == 'PAINT': # Remove these only if not isupdate
                            if not isupdate:
                                print(f"removed a node group: {ngroup.name}")
                                bpy.data.node_groups.remove(ngroup) 
                        elif ngroup['_up_type'] == 'MATERIAL':
                            bpy.data.node_groups.remove(ngroup) 
            
            for ngroup in bpy.data.node_groups:
                if ngroup.name == '_up_mask_fx' and ngroup.users == 0:
                    bpy.data.node_groups.remove(ngroup) 
                            
        # Finalize Transaction
        if not isupdate:
            obj.uberpaint.has_mask = False
            bpy.ops.ed.undo_push()  
            self.report({'INFO'}, "Material Removed Successfully")

        return {'FINISHED'}


class UP_OT_PaintMode(bpy.types.Operator):
    """Toggle painting mode for this layer"""
    bl_idname = "up.enter_paint_mode"
    bl_label = "Paint Layer"
    
    input_index : IntProperty(default=0)
    def execute(self, context):
        scene = context.scene
        obj = bpy.context.scene.uberpaint.target
        blend_mode = scene.uberpaint.target.uberpaint.mask_type
        materials = [entry.material for entry in scene.uberpaint.target.uberpaint.layers if entry.material]
        aod = obj.data
        input_index = self.input_index
        current_layer = 0
        
    # Toggle painting vs. object mode
        if blend_mode == "TEXTURE":
            if bpy.context.object.mode == 'OBJECT':
                bpy.ops.object.mode_set(mode='TEXTURE_PAINT')
                bpy.context.scene.tool_settings.image_paint.canvas = obj.uberpaint.layers[input_index].image_texture
                bpy.context.scene.tool_settings.image_paint.mode = 'IMAGE'
                
                if obj.uberpaint.layers[input_index].type == 'MATERIAL':
                    brush = bpy.context.tool_settings.image_paint.brush
                    brush.color = (1.0, 1.0, 1.0)
                    brush.secondary_color = (0.0, 0.0, 0.0)
                
            elif bpy.context.object.mode == 'TEXTURE_PAINT':
                if input_index == obj.uberpaint.layer_index:
                    bpy.ops.object.mode_set(mode='OBJECT')
                else:
                    bpy.context.scene.tool_settings.image_paint.canvas = obj.uberpaint.layers[input_index].image_texture
        elif blend_mode == "VERTEX":
            if bpy.context.object.mode == 'OBJECT':
                aod.vertex_colors.active = aod.vertex_colors[obj.uberpaint.layers[input_index].color_attr]
                bpy.ops.object.mode_set(mode='VERTEX_PAINT')
                
            elif bpy.context.object.mode == 'VERTEX_PAINT':
                if input_index == obj.uberpaint.layer_index:
                    bpy.ops.object.mode_set(mode='OBJECT')
                else:
                    aod.vertex_colors.active = aod.vertex_colors[obj.uberpaint.layers[input_index].color_attr]
                    
        current_layer = input_index
        obj.uberpaint.layer_index = input_index # Select the layer we're painting
        return {'FINISHED'}


class UP_OT_EditSource(bpy.types.Operator):
    """Edit this material. Affects the material for all users."""
    bl_idname = "up.edit_source"
    bl_label = "Edit Source Material"
    
    input_index : IntProperty(default=1)
                           
    def execute(self, context):
        scene = context.scene
        obj = scene.uberpaint.target
        materials = [entry.material for entry in obj.uberpaint.layers if entry.material]
        aod = obj.data
        input_index = self.input_index
        
        obj.active_material_index = input_index+1  # Activate the material slot with the material to be edited

        material = materials[input_index]
        if not material:
            self.report({'ERROR'}, f"Material '{self.material_name}' not found!")
            return {'CANCELLED'}
            
        # Create a temporary floating area
        bpy.ops.wm.window_new()
        new_window = bpy.context.window_manager.windows[-1]
        new_screen = new_window.screen

        # Change the first area in the new screen to a node editor
        for area in new_screen.areas:
            if area.type != 'NODE_EDITOR':
                area.type = 'NODE_EDITOR'
            # Set the space to the Shader Editor and focus on the material
            for space in area.spaces:
                if space.type == 'NODE_EDITOR':
                    space.tree_type = 'ShaderNodeTree'
                    space.node_tree = material.node_tree
                    break
        
        current_layer = input_index
        obj.uberpaint.layer_index = input_index # Select the layer we're editing
        return {'FINISHED'}


class UP_OT_CopyLayers(bpy.types.Operator):
    """Copy the layers from another object to the current target."""
    bl_idname = "up.copy_layers"
    bl_label = "Copy Layers"

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        target = scene.uberpaint.target
        copy_layers(obj, target)
        return {'FINISHED'}


class UP_OT_SetTargetObject(bpy.types.Operator):
    """Set the UberPaint target object to the active object in viewport"""
    bl_idname = "up.set_target"
    bl_label = "Set Target Object"
    def execute(self, context):
        scene = context.scene
        scene.uberpaint.target = context.active_object
        self.report({'INFO'}, "Target object set to active object")
        return {'FINISHED'}


class UP_UL_MaterialList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):       
        if item:
            # Add separate icons for texture vs. vertex painting
            scene = context.scene
            blend_mode = scene.uberpaint.target.uberpaint.mask_type
            mode_icon = None
            
            if blend_mode == "TEXTURE":
                mode_icon = "TPAINT_HLT"
            elif blend_mode == "VERTEX":
                mode_icon = "VPAINT_HLT"
            if (bpy.context.object.mode == "TEXTURE_PAINT" or bpy.context.object.mode == "VERTEX_PAINT") and scene.uberpaint.target.uberpaint.layer_index == index:  # Are we in texture paint mode and is the active layer selected?
                mode_icon = "BRUSH_DATA" 
            if index == scene.uberpaint.target.uberpaint.layer_index:
                layout.label(text="", icon="RADIOBUT_ON")
            else:
                layout.label(text="", icon="RADIOBUT_OFF")
                
            layergroup = item
            
            row = layout.row()
            row.enabled = (context.object.mode == 'OBJECT')
            layer_icon = get_layer_icon(index)
            row.prop(layergroup, "type", text="", icon=layer_icon, emboss=False, icon_only=True)
            
            if layergroup.type == 'MATERIAL':
                layout.prop(layergroup, "name", text="", emboss=False)
                layout.prop(layergroup, "material", text="")
            elif layergroup.type == 'PAINT':
                layout.prop(layergroup, "name", text="", emboss=False)
            
            row = layout.row()
            has_blend_mat = scene.uberpaint.target.uberpaint.has_mask
            
            if has_blend_mat == True:
                row.enabled = True
            elif has_blend_mat == False:
                row.enabled = False
                
            # Edit source material button
            if layergroup.type == 'MATERIAL':
                op = row.operator("up.edit_source", icon = "GREASEPENCIL", text="")
                op.input_index = index
                
            # Paint mode button
            op = row.operator("up.enter_paint_mode", icon = mode_icon, text="")
            op.input_index = index


class WM_OT_SettingsMenu(bpy.types.Operator):
    """Open generation settings"""
    bl_label = "Paint Mask Texture Settings"
    bl_idname = "wm.settingsmenu"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = scene.uberpaint.target
        
        warning_size = 512
        
        row=layout.row()
        row.prop(obj, "mask_type", text="")
        info=row.operator('wm.info', text ="", icon="QUESTION")
        info.message1="Painting Mode"
        info.message2="Image textures can work on models of any geometry density, but vertex colors work in real time in Cycles."
        
        row=layout.row()
        mask_res = row.prop(scene.uberpaint, "texture_resolution", text = "Mask Texture Size")
        
        settings_overview = str(scene.uberpaint.texture_resolution) + " x " + str(scene.uberpaint.texture_resolution)
        layout.label(text=settings_overview)
        if scene.texture_resolution > warning_size:
            layout.label(icon="ERROR", text="Sizes over "+str(warning_size)+"px are usually unecessary and can result in lag when painting.")

    def execute(self, context):
       # mask_width = res_x
        return {'FINISHED'}
    
    def invoke(self, context, event):     
        return context.window_manager.invoke_props_dialog(self)


class UP_SceneProps(bpy.types.PropertyGroup):  
    target: bpy.props.PointerProperty(type=bpy.types.Object, poll=obj_filter)
    texture_resolution: bpy.props.IntProperty(default=512)

class UP_LayerProps(bpy.types.PropertyGroup):
    name: StringProperty(default="Layer")
    id: StringProperty(default="")
    type: bpy.props.EnumProperty(name="Layer Type", description="Layers can represent materials and color paintings.  Set here.",
    items=[
        ('MATERIAL', "Material (Default)", "Paint material using a mask"),
        ('PAINT', "Paint", "Colorable custom paint layer; Ideal for graffiti"),
        #('GENERATOR', "Generator", "Use procedurals for coloring and displacement")
        ],
    default='MATERIAL', update=update_blendmat)
    material: bpy.props.PointerProperty(type=bpy.types.Material, poll=mat_filter)
    opacity: bpy.props.FloatProperty(name="opacity", default=1, min=0, max=1)
    mask_source: bpy.props.EnumProperty(name="Mask Source", description="Source that this layer's mask is derived from",
    items=[
        ('PAINT', "Paint Mask (Default)", "Use painted mask for blending"),
        ('AO', "Ambient Occlusion", "Use AO as the source, ideal for grunge"),
        ('NOISE', "Noise Texture", "Use a noise texture as the mask source")],
    default='PAINT', update=update_blendmat)   
    # Object specific properties
    image_texture: bpy.props.PointerProperty(type=bpy.types.Image)
    color_attr: StringProperty(default="")
    mixer_group: bpy.props.PointerProperty(type=bpy.types.ShaderNodeTree) 
    paint_group: bpy.props.PointerProperty(type=bpy.types.ShaderNodeTree) 

class UP_ObjectProps(bpy.types.PropertyGroup):
    layers: bpy.props.CollectionProperty(type=UP_LayerProps)
    layer_index: bpy.props.IntProperty(default=0)
    
    blend_mat: bpy.props.PointerProperty(type=bpy.types.Material)
    
    texture_resolution: bpy.props.IntProperty(default=512) # scene var
    mask_type: bpy.props.EnumProperty(
        name="Blend Mode",
        description="Choose blending method",
        items=[
            ('VERTEX', "Vertex Colors", "Use vertex colors for blending"),
            ('TEXTURE', "Image Textures", "Use image textures for blending")
        ],
        default='VERTEX', 
    )
    
    displacement_mode: bpy.props.EnumProperty(
    name="Displacement Mode",
    description="Choose shader displacement method",
    items=[
        ('BUMP', "Bump Only", ""),
        ('DISPLACEMENT', "Displacement Only", ""),
        ('BOTH', "Displacement and Bump", "")
    ],
    default='BUMP', update=update_blendmat
    )   
    has_mask: bpy.props.BoolProperty(
    name="Has Mask",
    description="Indicates whether this object has a mask",
    default=False)


###########################################################
# Registration
###########################################################

classes = [
    UP_LayerProps,
    UP_ObjectProps,
    UP_SceneProps,
    UP_UL_MaterialList,
    UP_PT_MainPanel,
    UP_PT_PropsPanel,
    UP_OT_ManageLayers,
    UP_OT_RebuildSourceGroup,
    UP_OT_GenerateMaterial,
    UP_OT_RemoveMaterial,
    WM_OT_SettingsMenu,
    WM_OT_InfoBox,
    UP_OT_PaintMode,
    UP_PT_PreferencesPanel,
    UP_OT_SetTargetObject,
    UP_PT_SupportPanel,
    UP_PT_ShaderPanel,
    UP_OT_EditSource,
    UP_OT_CopyLayers,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.uberpaint = bpy.props.PointerProperty(type=UP_ObjectProps)
    bpy.types.Scene.uberpaint = bpy.props.PointerProperty(type=UP_SceneProps)
    reload(up_materials)
    
def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    del bpy.types.Object.uberpaint # Removes attributes on objects?  Find out.
    del bpy.types.Scene.uberpaint

if __name__ == "__main__":
    register()