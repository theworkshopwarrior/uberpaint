bl_info = {
    "name": "UberPaint Beta",
    "description": "Quickly paint PBR materials using vertex colors or textures",
    "location": "N-Panel",
    "author": "Forest Stook",
    "version": (0, 7, 0),
    "blender": (4, 2, 0),
    "category": "Material",
    "warning": "UberPaint is still in development. Please report bugs to iotbot2010@gmail.com or theworkshopwarrior on Discord.",
}

links = {"Discord" : 'https://discord.gg/NQ68E2y26P',
         "Gumroad" : "https://theworkshopwarrior.gumroad.com/",
         }
         
#_TODO:_
# Don't open up popup if already up
# Add paint layers
# Improve stability by preventing user from going too fast?
# Don't import multiple maskfx groups from mixer.blend
# -- Lesser priority
# Noise texture blending
# More comprehensive UI help buttons
# Custom Mask Presets
# Fix nodetree organization in 4.3-

# _DONE:_
#--- 0.7:
# Redo node tree creation
# Test and fix for 4.2 - 4.4
# Disable changing of mask sourcein non object mode
# Auto updates after changing displacement mode
# INVESTIGATE UPDATE GROUP + AUTO UPDATE

import bpy, mathutils, textwrap

from bpy import context
from bl_ui.generic_ui_list import draw_ui_list

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
    material_to_group
)

bpy.types.Scene.target = bpy.props.PointerProperty(type=bpy.types.Object)

# --- SETTINGS ---
up_version = 0.7
up_info = "Beta"
bl_version = bpy.app.version
#---------------

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
        obj = context.scene.target
        
        # if not obj:
            # return
        row = layout.row()
        row.prop_search(context.scene, "target", context.scene, "objects", text="Target Object")
        row.operator("ll.set_target", text="", icon="MOD_LINEART")
        
        if obj:
            layout.label(text="Layers:")   
            
            row = layout.row()
            
            row.template_list("UP_UL_MaterialList", "", obj, "ll_materials", obj, "ll_material_index")
            
            col = row.column(align=True)
            col.enabled = obj.mode == "OBJECT"
            
            col.operator("ll.manage_material", icon='ADD', text="").action = 'ADD'
            col.operator("ll.manage_material", icon='REMOVE', text="").action = 'REMOVE'
            #col.separator()
            #col.menu("MATERIAL_MT_context_menu", icon='DOWNARROW_HLT', text="")
            col.separator()
            col.operator("ll.manage_material", icon='TRIA_UP', text="").action = 'UP'
            col.operator("ll.manage_material", icon='TRIA_DOWN', text="").action = 'DOWN'
            
            if not scene.target.has_mask:
                layout.label(text="Mask Target:")
                layout.prop(obj, "ll_blend_mode", text="")
            
            # Layer generation button
            row = layout.row()
            row.enabled = bpy.context.object.mode == "OBJECT"
            row.scale_y = 1.5
            
            if scene.target.has_mask:
                row.operator("ll.generate_material", text="Update Blend Material", icon="FILE_REFRESH").action = True
            else:
                row.operator("ll.generate_material", text="Generate Blend Material", icon="SHADERFX").action = False
                _settings_menu = row.operator("wm.settingsmenu", text="", icon="PREFERENCES")
                #_settings_menu.enabled = not(scene.target.has_mask)
            #------------------------------------
            
            # Layer deletion button
            row = layout.row()
            row.enabled = scene.target.has_mask and bpy.context.object.mode == "OBJECT"
            row.operator("ll.remove_material", text="Remove Blend Material", icon="TRASH")
            
            layout.separator()
            if scene.target.has_mask:
                layout.prop(obj, "ll_disp_mode", text="Displacement Mode")

    
class UP_PT_PropsPanel(bpy.types.Panel):
    bl_label = "Layer Properties"
    bl_idname = "UP_PT_PropsPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'UberPaint'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.scene.target
        active_layer = get_active_layer(context)
        
        
        if obj and obj.has_mask:
            box = layout.box()
            box.enabled = (bpy.context.object.mode == 'OBJECT')
            mgroup = active_layer.mixer_group
            
            mask_src = active_layer.mask_source
            box.prop(active_layer, 'mask_source')
            
            if mask_src == "AO" and mgroup.nodes.get('src_ao'):
                box.template_node_inputs(mgroup.nodes['src_ao'])
            if mask_src == "NOISE" and mgroup.nodes.get('src_noise'):
                box.template_node_inputs(mgroup.nodes['src_noise'])
            
            layout.label(text="Mask Adjustments")
            box = layout.box()          
            row = box.row()
            opacity_node = mgroup.nodes["opacity"]
            socket = opacity_node.inputs[0]
            row.label(text="Opacity")
            socket.draw(context, row, opacity_node, socket.name) # Opacity Slider
            box.label(text="Mask Controls:")
            mgroup.nodes["color_adjustments"].draw_buttons(context, box) # Color Ramp
            
            box = layout.box()
            # tex = context.texture
            # layout.template_image(active_layer, "image", tex.image_user)
            
            box.label(text="Displacement Blending")
            fx_node = mgroup.nodes["ngroup_up_mask_fx"]
            disp_node = mgroup.nodes["disp_blending_tex"]
            
            disp_node.draw_buttons(context, layout)
            for input_socket in fx_node.inputs:
                if not input_socket.is_linked:
                    layout.prop(input_socket, "default_value", text=input_socket.name)
            
            
        else:
            box = layout.box()
            box.label(text="Please generate a blend material.  "+goofy_insult(), icon="ERROR")


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
        obj = context.scene.target
        mat = obj.active_material
        materials = [entry.material for entry in obj.ll_materials if entry.material]  
        
        if obj and bl_version > (4, 1, 0):
            row = layout.row()
            row.scale_y = 3
            row.enabled = obj.has_mask and (mat in materials)
            row.alert = True
            row.operator("ll.rebuild_src", text=f"Update this Group", icon="FILE_REFRESH", icon_value=656, emboss=True)


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
    width = 40
    
    def execute(self, context):
        return {'FINISHED'}
 
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width = 400)
 
    def draw(self, context):
        layout = self.layout
        
        layout.label(icon=str(self.icon), text=str(self.message1))
        
        # Wrapping to avoid overflow
        
        textTowrap = self.message2    
        wrapp = textwrap.TextWrapper(width=60)    
        wList = wrapp.wrap(text=textTowrap) 
        
        box=layout.box()
        for text in wList: 
            row = box.row(align = True)
            row.alignment = 'EXPAND'
            row.scale_y = 0.6
            row.label(text=text)


class UP_OT_GenerateMaterial(bpy.types.Operator):
    """Generate a blend material for the target object"""
    bl_idname = "ll.generate_material"
    bl_label = "Generate Layer Material"
    # bl_options = {'REGISTER', 'UNDO'}
    
    action: bpy.props.BoolProperty(False) # False for generation, true for updates
    
    def execute(self, context):
        wm = bpy.context.window_manager
        wm.progress_begin(0, 100)
        
        scene = context.scene
        active_object = bpy.context.scene.target
        blend_mode = context.scene.target.ll_blend_mode
        materials = [entry.material for entry in scene.target.ll_materials if entry.material]       
        mesh_dat = active_object.data

        if self.action == True: 
            bpy.ops.ll.remove_material(isupdate=True)
            
        # Preliminary checks to avoid disaster
        if active_object.type != "MESH":
            self.report({'WARNING'}, "Target object is not a mesh.  " + goofy_insult())
            return {'CANCELLED'}
        if len(materials) < 2:
            self.report({'WARNING'}, "Please select at least two materials.  " + goofy_insult())
            return {'CANCELLED'}
            
        all_materials = [entry.material for entry in scene.target.ll_materials] 
        for m in all_materials or (scene.target.ll_material_index < len(scene.target.ll_materials)):
            if not m:
                self.report({'WARNING'}, "Please remove unused material slots!  " + goofy_insult())
                return {'CANCELLED'}            
            
        # Remove all material slots
        active_object.data.materials.clear()
                
        # Select and activate target; This may be removed soon.         
        active_object.select_set(True)
        bpy.context.view_layer.objects.active = active_object
        bpy.ops.object.select_all(action='DESELECT')
        active_object.select_set(True)
        
        # -----Create Blend Material-----
        blend_mat_name = active_object.name + " Blend Mat"
        
        # Check if this object already has a material
        if any(mat and mat.name == blend_mat_name for mat in active_object.data.materials):
            self.report({'WARNING'}, "This object already has a blend material.  " + goofy_insult())
            return {'CANCELLED'}
         
        mask_res = scene.ll_texture_resolution
        # Ready to go?  Check if we're using an image or a vertex texture and add attributes accordingly.     
        obj_image_textures =[]
        obj_vgroups = []
        if blend_mode == "TEXTURE":
            if '_upm_paintUVs' not in active_object.data.uv_layers:
                tex_UVs = active_object.data.uv_layers.new(name="_upm_paintUVs")
                mesh_dat.uv_layers.active = mesh_dat.uv_layers["_upm_paintUVs"]
                active_object.select_set(True)
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_mode(type="FACE")
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.03)
                bpy.ops.object.mode_set(mode='OBJECT')
            
            i = 0
            images = []
            for mat in materials:
                attr_name = "_upm: "+active_object.name+" - "+mat.name
                images.append(attr_name)
                i += 1
                
            rep=0
            for i in materials:
                attr_name = "_upm: "+active_object.name+" - "+i.name
                if not bpy.data.images.get(attr_name):
                    image_tex = bpy.data.images.new(attr_name, width=mask_res, height=mask_res)
                    
                    if rep == len(materials)-1 and not self.action:
                        image_tex.pixels = [1.0, 1.0, 1.0, 1.0] * (mask_res * mask_res)
                    else:
                        image_tex.pixels = [0.0, 0.0, 0.0, 1.0] * (mask_res * mask_res)
                    image_tex.pack()
                    print(image_tex)
                    obj_image_textures.append(image_tex)
                    active_object.ll_materials[rep].image_texture = image_tex
                    print("Added:" +image_tex.name)
                print(active_object.ll_materials[rep].image_texture)
                rep+=1
                          
        elif blend_mode == "VERTEX":          
            i = 0    
            for mat in materials:
                attr_name = "_upm: "+active_object.name+" - "+mat.name
                active_object.ll_materials[i].color_attr = attr_name
                i += 1
            
            i = 0 
            ngroups = active_object.data.vertex_colors
            valid_vcols = [vcol.name for vcol in ngroups if vcol.name.startswith('_upm: '+active_object.name+" - ")]      
            vcols_to_add = {mat.color_attr for mat in active_object.ll_materials}

            for vcol in vcols_to_add:
                if (vcol not in valid_vcols):
                    avc = active_object.data.vertex_colors.new(name=vcol)  
                    # Set vertex colors to black on all but bottom layer
                    for loop in mesh_dat.loops:
                        avc.data[loop.index].color = (0, 0, 0, 1.0) 
                if not self.action:
                    if active_object.ll_materials[len(materials)-1].color_attr == vcol:
                        avc = mesh_dat.vertex_colors[vcol]
                        for loop in mesh_dat.loops:
                            avc.data[loop.index].color = (1, 1, 1, 1.0)   
                i+=1
            
        wm.progress_update(50)
        ##############################################
        # This is where the magic happens.  Adding the node groups to the material
        mixer_groups = []
        converted_mats = []
        blend_mat = bpy.data.materials.new(blend_mat_name)
        blend_mat.use_nodes = True
        if bl_version < (4, 1, 0):
            blend_mat.cycles.displacement_method = active_object.ll_disp_mode
        else: 
            blend_mat.displacement_method = active_object.ll_disp_mode
            
        is_tex = True if blend_mode == "TEXTURE" else (False if blend_mode == "VERTEX" else None)
        rep=0
        
        for m in materials:
            mixer_name = "_up_"+m.name + " - " + active_object.name + "_mixer"   
            
            mixer_groups.append(up_mixer_node_group(mixer_name, is_tex, "_upm: "+active_object.name+" - "+m.name, "_upm_paintUVs", active_object.ll_materials[rep].image_texture, active_object.ll_materials[rep].mask_source, self))
            layer_group = material_to_group(m, active_object.name)
            converted_mats.append(layer_group)
            active_object.ll_materials[rep].mixer_group = mixer_groups[rep]
            get_active_layer(context).mixer_group
            
            rep+=1
        
        bg_col = context.preferences.addons[__name__].preferences.bg_color
        up_blendmat_node_group(blend_mat, converted_mats, mixer_groups, bg_col)
            
        scene.target.has_mask = True
        blend_mat.use_nodes = True
        
        active_object.data.materials.append(blend_mat)
        scene.target.ll_blend_material = blend_mat
        
        # Add all source materials so they can be previewed/easily edited
        for mat in materials:
            if mat:
                active_object.data.materials.append(mat)  # Add material slot
                
        wm.progress_update(100)
        wm.progress_end()
        bpy.ops.ed.undo_push()        
        self.report({'INFO'}, "Material Created Successfully")        
        return {'FINISHED'}


class UP_OT_ManageMaterials(bpy.types.Operator):
    bl_idname = "ll.manage_material"
    bl_label = "Manage Material"
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
        materials = scene.target.ll_materials
        index = scene.target.ll_material_index
        if self.action == 'ADD':
            new_mat = materials.add()
            new_mat.material = None
            scene.target.ll_material_index = len(materials) - 1
        elif self.action == 'REMOVE' and index >= 0:
            materials.remove(index)
            scene.target.ll_material_index = max(0, index - 1)
        elif self.action == 'UP' and index > 0:
            materials.move(index, index - 1)
            scene.target.ll_material_index -= 1
        elif self.action == 'DOWN' and index < len(materials) - 1:
            materials.move(index, index + 1)
            scene.target.ll_material_index += 1
        
        if scene.target.has_mask and self.action != 'ADD':
            if index < len(scene.target.ll_materials):
                if scene.target.ll_materials[index].material is not None:
                    bpy.ops.ll.generate_material(action=True)
        
        return {'FINISHED'}


class UP_OT_RebuildSourceGroup(bpy.types.Operator):
    """Refresh the current source material's node tree"""
    bl_idname = "ll.rebuild_src"
    bl_label = "Rebuild Group"
    
    def execute(self, context): 
        scene = context.scene
        obj = scene.target
        materials = [entry.material for entry in obj.ll_materials if entry.material]    
        mat_index = obj.active_material_index
        blend_mat = obj.ll_blend_material
        
        material = obj.active_material
        group_name = str(f"_up_{obj.name} - {material.name}")
        for node in blend_mat.node_tree.nodes:
            if node.type == 'GROUP':
                if node.node_tree.name == group_name:
                    bpy.data.node_groups.remove(bpy.data.node_groups[group_name]) 
                    layer_group = material_to_group(material, obj.name)
                    blend_mat.node_tree.nodes[group_name].node_tree = layer_group
                  
                    self.report({'INFO'}, f"Blend Material Updated: {material.name}")        
        return {'FINISHED'}


class UP_OT_RemoveMaterial(bpy.types.Operator):
    """Remove and clean up the target object's blend materal"""
    bl_idname = "ll.remove_material"
    bl_label = "Remove Blend Material"
    
    isupdate: bpy.props.BoolProperty(False) # False for full removal, true for updates
    
    def execute(self, context):
        scene = context.scene
        active_object = bpy.context.scene.target
        blend_mode = context.scene.target.ll_blend_mode
        materials = [entry.material for entry in scene.target.ll_materials if entry.material]
        isupdate = self.isupdate
        
        # Check if the target already has a blend mat
        if scene.target.has_mask == False:
            return {'CANCELLED'}
        
        active_object.select_set(True)
        bpy.context.view_layer.objects.active = active_object
        bpy.ops.object.select_all(action='DESELECT')
        active_object.select_set(True)
        
        m = active_object.ll_blend_material
        if not m:
            self.report({'WARNING'}, "We couldn't find the blend material. Did you delete it? Try regenerating.")
            scene.target.has_mask = False
            bpy.ops.active_object.material_slot_remove()
            return {'CANCELLED'}
        
        
        bpy.data.materials.remove(m)
        bpy.ops.object.material_slot_remove()
        
        # Remove UVs :D
        if not(isupdate) and '_upm_paintUVs' in active_object.data.uv_layers:
            uv_layer = active_object.data.uv_layers['_upm_paintUVs']
            active_object.data.uv_layers.remove(layer=uv_layer)
        
        # Remove Image Textures
        upm_images = [img for img in bpy.data.images if img.name.startswith("_upm: "+active_object.name+" - ")]
        obj_texs = [entry.image_texture for entry in active_object.ll_materials if entry.image_texture] 
        if upm_images:
            if isupdate:
                for img in upm_images:
                    if not img.users:  # Check if the image has no real users
                        bpy.data.images.remove(img)  # Remove the image
            else:
                for img in bpy.data.images:
                    if img.name.startswith('_upm: '+active_object.name+" - "):
                        bpy.data.images.remove(img)
        
        # # Remove Color Attributes :D
        vcol_layers = active_object.data.vertex_colors
        vcols = [vcol for vcol in vcol_layers if vcol.name.startswith('_upm: '+active_object.name+" - ")]      
        if hasattr(active_object.data, "vertex_colors") and len(vcols)>0: # and active_object.ll_blend_mode == "VERTEX":
            obj_clrs = [entry.color_attr for entry in active_object.ll_materials if entry.color_attr] 
            vcols = []
            for color_attr in obj_clrs:
                vcols.append(active_object.data.vertex_colors[color_attr])
            vcols.reverse()
            
            vt_colors = active_object.data.vertex_colors
            
            if isupdate:  
                rep = 0
                for vcol in vcols:
                    if vcol not in list(vt_colors):
                        vt_colors.remove(vcol)
                        rep+=1
            else:
                vcol_layers = active_object.data.vertex_colors
                vcols = [vcol for vcol in vcol_layers if vcol.name.startswith('_upm: '+active_object.name+" - ")]
                vcols.reverse() # Do this or else strange things happen
                for vcol in vcols:
                    vt_colors.remove(vcol)
                        
        # Remove node groups
        ngroups = bpy.data.node_groups
        ngroups_to_remove = [ngroup for ngroup in ngroups if (ngroup.name.startswith('_up_'+active_object.name+" - ") or ngroup.name.endswith(active_object.name+"_mixer") or ngroup.name.startswith('_up_mask_fx'))]      
        valid_mixer_groups = {mat.mixer_group.name for mat in active_object.ll_materials if mat.mixer_group}
        
        for ngroup in ngroups_to_remove:
            if not isupdate or (ngroup.name not in valid_mixer_groups):
                if ngroup.name.startswith("_up_mask_fx"):
                    if ngroup.users == 0:
                        bpy.data.node_groups.remove(ngroup) 
                else:
                    bpy.data.node_groups.remove(ngroup)    
                
        # Finalize Transaction
        if not isupdate:
            bpy.ops.ed.undo_push()  
            
        scene.target.has_mask = False
        self.report({'INFO'}, "Material Removed Successfully")
        return {'FINISHED'}


class UP_OT_PaintMode(bpy.types.Operator):
    """Toggle painting mode for this layer"""
    bl_idname = "ll.enter_paint_mode"
    bl_label = "Paint Layer"
    
    input_index : IntProperty(default=0)
    def execute(self, context):
        scene = context.scene
        active_object = bpy.context.scene.target
        blend_mode = scene.target.ll_blend_mode
        materials = [entry.material for entry in scene.target.ll_materials if entry.material]
        aod = active_object.data
        input_index = self.input_index
        current_layer = 0
        
    # Toggle painting vs. object mode
        if blend_mode == "TEXTURE":
            if bpy.context.object.mode == 'OBJECT':
                bpy.ops.object.mode_set(mode='TEXTURE_PAINT')
                bpy.context.scene.tool_settings.image_paint.canvas = active_object.ll_materials[input_index].image_texture
                bpy.context.scene.tool_settings.image_paint.mode = 'IMAGE'

                
            elif bpy.context.object.mode == 'TEXTURE_PAINT':
                if input_index == active_object.ll_material_index:
                    bpy.ops.object.mode_set(mode='OBJECT')
                else:
                    bpy.context.scene.tool_settings.image_paint.canvas = active_object.ll_materials[input_index].image_texture
        elif blend_mode == "VERTEX":
            if bpy.context.object.mode == 'OBJECT':
                aod.vertex_colors.active = aod.vertex_colors[active_object.ll_materials[input_index].color_attr]
                bpy.ops.object.mode_set(mode='VERTEX_PAINT')
                
            elif bpy.context.object.mode == 'VERTEX_PAINT':
                if input_index == active_object.ll_material_index:
                    bpy.ops.object.mode_set(mode='OBJECT')
                else:
                    aod.vertex_colors.active = aod.vertex_colors[active_object.ll_materials[input_index].color_attr]
                    
        current_layer = input_index
        active_object.ll_material_index = input_index # Select the layer we're painting
        return {'FINISHED'}


class UP_OT_EditSource(bpy.types.Operator):
    """Edit this material. Affects the material for all users."""
    bl_idname = "ll.edit_source"
    bl_label = "Edit Source Material"
    
    input_index : IntProperty(default=1)

                                
    def execute(self, context):
        scene = context.scene
        obj = scene.target
        materials = [entry.material for entry in obj.ll_materials if entry.material]
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
        obj.ll_material_index = input_index # Select the layer we're editing
        return {'FINISHED'}


class UP_OT_SetTargetObject(bpy.types.Operator):
    """Set the UberPaint target object to the active object in viewport"""
    bl_idname = "ll.set_target"
    bl_label = "Set Target Object"
    def execute(self, context):
        scene = context.scene
        scene.target = context.active_object
        self.report({'INFO'}, "Target object set to active object")
        return {'FINISHED'}


class UP_UL_MaterialList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        
    # Add seperate icons for texture vs. vertex painting
        scene = context.scene
        blend_mode = scene.target.ll_blend_mode
        mode_icon = None
        
        if blend_mode == "TEXTURE":
            mode_icon = "TPAINT_HLT"
        elif blend_mode == "VERTEX":
            mode_icon = "VPAINT_HLT"
        if (bpy.context.object.mode == "TEXTURE_PAINT" or bpy.context.object.mode == "VERTEX_PAINT") and scene.target.ll_material_index == index:  # Are we in texture paint mode and is the active layer selected?
            mode_icon = "BRUSH_DATA"
    # Draw layers UIlist  
        if index == scene.target.ll_material_index:
            layout.label(text="", icon="RADIOBUT_ON")
        else:
            layout.label(text="", icon="RADIOBUT_OFF")
            
        layergroup = item
        layout.prop(layergroup, "material", text="")
        
        row = layout.row()
        has_blend_mat = scene.target.has_mask
        
        if has_blend_mat == True:
            row.enabled = True
        elif has_blend_mat == False:
            row.enabled = False
            
        # layout.prop(layergroup, "opacity", text="Opacity", slider=True)  
        # Paint mode button
        op = row.operator("ll.enter_paint_mode", icon = mode_icon, text="")
        op.input_index = index
        
        # Edit source material button
        op = row.operator("ll.edit_source", icon = "GREASEPENCIL", text="")
        op.input_index = index


class WM_OT_SettingsMenu(bpy.types.Operator):
    """Open generation settings"""
    bl_label = "Paint Mask Texture Settings"
    bl_idname = "wm.settingsmenu"
    
    
    #res_x : bpy.props.IntProperty(name="Resolution", default = 1024)
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = scene.target
        
        warning_size = 512
        
        row=layout.row()
        row.prop(obj, "ll_blend_mode", text="")
        info=row.operator('wm.info', text ="", icon="QUESTION")
        info.message1="Painting Mode"
        info.message2="Image textures can work on models of any geometry density, but vertex colors work in real time in Cycles."
        
        row=layout.row()
        mask_res = row.prop(scene, "ll_texture_resolution", text = "Mask Texture Size")
        
        settings_overview = str(scene.ll_texture_resolution) + " x " + str(scene.ll_texture_resolution)
        layout.label(text=settings_overview)
        if scene.ll_texture_resolution > warning_size:
            layout.label(icon="ERROR", text="Sizes over "+str(warning_size)+"px are usually unecessary and can result in lag when painting.")

    def execute(self, context):
       # mask_width = res_x
        return {'FINISHED'}
    
    def invoke(self, context, event):     
        return context.window_manager.invoke_props_dialog(self)


def update_blendmat(self, context):
    bpy.ops.ll.generate_material(action=True)


class UP_MaterialEntry(bpy.types.PropertyGroup):
    material: bpy.props.PointerProperty(type=bpy.types.Material)
    image_texture: bpy.props.PointerProperty(type=bpy.types.Image)
    color_attr: StringProperty(default="")
    mixer_group: bpy.props.PointerProperty(type=bpy.types.ShaderNodeTree) 
    opacity: bpy.props.FloatProperty(name="opacity", default=1, min=0, max=1)
    mask_source: bpy.props.EnumProperty(name="Mask Source", description="Source that this layer's mask is derived from",
    items=[
        ('PAINT', "Paint (Default)", "Use painted mask for blending"),
        ('AO', "Ambient Occlusion", "Use AO as the source, ideal for grunge"),
        ('NOISE', "Noise Texture", "Use a noise texture as the mask source")],
    default='PAINT', update=update_blendmat)

###########################################################
# Functions
###########################################################

def get_active_layer(context):
    """Retrieve the currently active layer based on index."""
    scene = context.scene
    target = scene.target 
    if hasattr(target, "ll_materials") and len(target.ll_materials) > target.ll_material_index:
        return target.ll_materials[target.ll_material_index]
    return None

def update_tweaks(self, context):
    scene = context.scene
    material = self.material
                                
###########################################################
# Registration
###########################################################

classes = [
    UP_UL_MaterialList,
    UP_PT_MainPanel,
    UP_PT_PropsPanel,
    UP_OT_ManageMaterials,
    UP_OT_RebuildSourceGroup,
    UP_OT_GenerateMaterial,
    UP_OT_RemoveMaterial,
    UP_MaterialEntry,
    WM_OT_SettingsMenu,
    WM_OT_InfoBox,
    UP_OT_PaintMode,
    UP_PT_PreferencesPanel,
    UP_OT_SetTargetObject,
    UP_PT_SupportPanel,
    UP_PT_ShaderPanel,
    UP_OT_EditSource
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.ll_materials = bpy.props.CollectionProperty(type=UP_MaterialEntry)
    bpy.types.Object.ll_material_index = bpy.props.IntProperty(default=0)
    
    bpy.types.Object.ll_blend_material = bpy.props.PointerProperty(type=bpy.types.Material)
    
    bpy.types.Scene.ll_texture_resolution = bpy.props.IntProperty(default=256) # scene var
    bpy.types.Object.ll_blend_mode = bpy.props.EnumProperty(
        name="Blend Mode",
        description="Choose blending method",
        items=[
            ('VERTEX', "Vertex Colors", "Use vertex colors for blending"),
            ('TEXTURE', "Image Textures", "Use image textures for blending")
        ],
        default='VERTEX', 
    )
    
    bpy.types.Object.ll_disp_mode = bpy.props.EnumProperty(
    name="Displacement Mode",
    description="Choose shader displacement method",
    items=[
        ('BUMP', "Bump Only", ""),
        ('DISPLACEMENT', "Displacement Only", ""),
        ('BOTH', "Displacement and Bump", "")
    ],
    default='BUMP', update=update_blendmat
    )
    
    bpy.types.Object.has_mask = bpy.props.BoolProperty(
    name="Has Mask",
    description="Indicates whether this object has a mask",
    default=False)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Object.ll_materials
    del bpy.types.Object.ll_material_index
    del bpy.types.Object.ll_blend_mode

  
if __name__ == "__main__":
    register()