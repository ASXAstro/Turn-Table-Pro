bl_info = {
    "name": "Turn Table Pro",
    "author": "Custom",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Turn Table Pro",
    "description": "Professional Master/Slave Turntable Sync. Works across all files.",
    "category": "3D View",
}

import bpy
import bmesh
import math
import time
import os
import json
from mathutils import Vector, Quaternion
from bpy.app.handlers import persistent

BRIDGE_FILE = os.path.join(bpy.utils.user_resource('CONFIG'), ".blender_turntable_cast.json")

# ------------------------------------------------------------
# Core Engine Logic
# ------------------------------------------------------------

class RotationEngine:
    def __init__(self):
        self.last_time = time.time()
        self.start_time = time.time()
        
        # Network Optimization Variables
        self.last_io_time = 0.0
        self.io_interval = 1.0 / 60.0  # Throttle Read/Write to 60 FPS
        
        # Interpolation Targets
        self.target_rot = None
        self.target_loc = None
        self.target_dist = None
        self.target_lens = None

    def update(self, context):
        # Safety check for scene data
        if not context or not hasattr(context, "scene") or not hasattr(context.scene, "turntable_props"):
            return 

        props = context.scene.turntable_props
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        
        # Get Viewport
        try:
            rv3d = next((a.spaces.active.region_3d for w in context.window_manager.windows for a in w.screen.areas if a.type == 'VIEW_3D'), None)
            space = next((a.spaces.active for w in context.window_manager.windows for a in w.screen.areas if a.type == 'VIEW_3D'), None)
        except: return
        
        if not rv3d or not space: return

        # 1. Sync Logic (Read/Write at 60fps max)
        if props.is_casting:
            if now - self.last_io_time >= self.io_interval:
                self.write_sync_file(props, rv3d, space)
                self.last_io_time = now
                
        elif props.is_receiving:
            if now - self.last_io_time >= self.io_interval:
                self.read_sync_file(props, rv3d, space)
                self.last_io_time = now
            
            # Smoothly interpolate viewport every frame (up to 100fps via timer)
            self.interpolate_viewport(rv3d, space, dt)

        # 2. Rotation Logic (DISABLED if receiving, let interpolation handle it)
        if props.running and not props.is_receiving:
            axis_vec = Vector((1,0,0)) if props.axis == 'X' else Vector((0,1,0)) if props.axis == 'Y' else Vector((0,0,1))
            
            if props.rotation_mode == 'TURNTABLE':
                angle = props.speed * dt
            elif props.rotation_mode == 'MICRO':
                angle = math.radians(props.sweep_angle) * props.speed * math.cos(props.speed * (now - self.start_time)) * dt
            else:
                angle = (props.speed + math.radians(props.osc_magnitude) * props.osc_speed * math.cos(props.osc_speed * (now - self.start_time))) * dt
            
            dq = Quaternion(axis_vec, angle)
            pivot = self.get_dynamic_pivot(context, props)
            
            rv3d.view_location = pivot + dq @ (rv3d.view_location - pivot)
            rv3d.view_rotation = dq @ rv3d.view_rotation

    def interpolate_viewport(self, rv3d, space, dt):
        """Linearly/Spherically interpolates current transform to target transform."""
        if self.target_rot is None:
            return
            
        # Exponential smoothing factor based on delta time (15.0 is a responsive smoothness multiplier)
        factor = 1.0 - math.exp(-15.0 * dt)
        
        rv3d.view_rotation = rv3d.view_rotation.slerp(self.target_rot, factor)
        rv3d.view_location = rv3d.view_location.lerp(self.target_loc, factor)
        rv3d.view_distance += (self.target_dist - rv3d.view_distance) * factor
        space.lens += (self.target_lens - space.lens) * factor

    def get_dynamic_pivot(self, context, props):
        obj = context.view_layer.objects.active
        cursor_loc = context.scene.cursor.location.copy()
        
        if obj and obj.mode == 'EDIT' and obj.type == 'MESH':
            bm = bmesh.from_edit_mesh(obj.data)
            sel = [obj.matrix_world @ v.co for v in bm.verts if v.select]
            return sum(sel, Vector()) / len(sel) if sel else obj.matrix_world.translation.copy()

        selected = context.view_layer.objects.selected
        if not selected: return cursor_loc
        if props.pivot_mode == 'CURSOR': return cursor_loc
        if props.pivot_mode == 'OBJECT' and obj: return obj.matrix_world.translation.copy()
        return sum((o.matrix_world.translation for o in selected), Vector()) / len(selected)

    def write_sync_file(self, props, rv3d, space):
        data = {
            "rot": list(rv3d.view_rotation), "loc": list(rv3d.view_location),
            "dist": rv3d.view_distance, "lens": space.lens, "running": props.running,
            "mode": props.rotation_mode, "axis": props.axis, "pivot": props.pivot_mode,
            "speed": props.speed, "sweep": props.sweep_angle, "osc_amp": props.osc_magnitude,
            "osc_freq": props.osc_speed, "time": time.time()
        }
        try:
            with open(BRIDGE_FILE, 'w') as f: json.dump(data, f)
        except: pass

    def read_sync_file(self, props, rv3d, space):
        if not os.path.exists(BRIDGE_FILE): return
        try:
            with open(BRIDGE_FILE, 'r') as f: data = json.load(f)
            props.running = data.get("running", False)
            props.rotation_mode = data.get("mode", props.rotation_mode)
            props.axis = data.get("axis", props.axis)
            props.speed = data.get("speed", props.speed)
            
            # Read new targets
            rot = Quaternion(data["rot"])
            loc = Vector(data["loc"])
            dist = data["dist"]
            lens = data.get("lens", space.lens)
            
            # Snap instantly if targets were empty (initial enable)
            if self.target_rot is None:
                rv3d.view_rotation = rot
                rv3d.view_location = loc
                rv3d.view_distance = dist
                space.lens = lens
            
            # Assign targets for interpolation
            self.target_rot = rot
            self.target_loc = loc
            self.target_dist = dist
            self.target_lens = lens
        except: pass

engine = RotationEngine()

# ------------------------------------------------------------
# Handlers & Timers
# ------------------------------------------------------------

def sync_timer():
    if engine:
        engine.update(bpy.context)
    return 0.01  # Interpolation core runs at ~100fps for butter smooth tracking

@persistent
def load_post_handler(dummy):
    """Triggered every time a file is opened."""
    if not bpy.app.timers.is_registered(sync_timer):
        bpy.app.timers.register(sync_timer)

# ------------------------------------------------------------
# Property Callbacks & UI Updates
# ------------------------------------------------------------

def popup_receiver_warning(self, context):
    """Draws the content of the popup menu."""
    self.layout.label(text="Move the viewport from Caster Viewport/window", icon='INFO')

def update_cast_mode(self, context):
    """Fired when Cast is toggled."""
    if self.is_casting:
        self.is_receiving = False

def update_receive_mode(self, context):
    """Fired when Receiver is toggled."""
    if self.is_receiving:
        self.is_casting = False
        # Trigger popup menu
        context.window_manager.popup_menu(popup_receiver_warning, title="Receiver Mode Active", icon='VIEW3D')
    else:
        # Clear interpolation targets so it snaps fresh next time it's turned on
        engine.target_rot = None
        engine.target_loc = None

# ------------------------------------------------------------
# UI & Boilerplate
# ------------------------------------------------------------

class TurntableProps(bpy.types.PropertyGroup):
    running: bpy.props.BoolProperty(default=False)
    
    # Updated Network Properties
    is_casting: bpy.props.BoolProperty(name="Cast", default=False, update=update_cast_mode)
    is_receiving: bpy.props.BoolProperty(name="Receiver", default=False, update=update_receive_mode)
    
    axis: bpy.props.EnumProperty(items=[('X',"X",""),('Y',"Y",""),('Z',"Z","")], default='Z')
    pivot_mode: bpy.props.EnumProperty(items=[('AUTO','Auto',''),('CURSOR','Cursor',''),('OBJECT','Origin','')], default='AUTO')
    speed: bpy.props.FloatProperty(name="Speed", default=1.0)
    rotation_mode: bpy.props.EnumProperty(items=[('TURNTABLE',"Turntable",""),('MICRO',"Sweep",""),('INSPECT',"Inspect","")], default='TURNTABLE')
    sweep_angle: bpy.props.FloatProperty(name="Sweep", default=45)
    osc_magnitude: bpy.props.FloatProperty(name="Osc Amp", default=40)
    osc_speed: bpy.props.FloatProperty(name="Osc Freq", default=4.5)

class VIEW3D_OT_turntable_run(bpy.types.Operator):
    bl_idname = "view3d.turntable_run"; bl_label = "Toggle Turntable"
    def execute(self, context):
        context.scene.turntable_props.running = not context.scene.turntable_props.running
        engine.start_time = time.time()
        return {'FINISHED'}

class VIEW3D_PT_turntable_panel(bpy.types.Panel):
    bl_label = "Turn Table Pro"; bl_idname = "VIEW3D_PT_turntable_sync"
    bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = "Turn Table Pro"
    def draw(self, context):
        layout = self.layout
        props = context.scene.turntable_props
        
        box = layout.box()
        row = box.row(align=True)
        
        # Cast Button (Disabled if Receiving is ON)
        cast_row = row.row(align=True)
        cast_row.enabled = not props.is_receiving
        cast_row.prop(props, "is_casting", text="CAST", icon='RADIOBUT_ON' if props.is_casting else 'RADIOBUT_OFF', toggle=True)
        
        # Receiver Button (Disabled if Casting is ON)
        rcv_row = row.row(align=True)
        rcv_row.enabled = not props.is_casting 
        rcv_row.prop(props, "is_receiving", text="RECEIVER", icon='IMPORT', toggle=True)
        
        col = layout.column(align=True)
        col.prop(props, "rotation_mode")
        row = col.row(align=True)
        row.prop(props, "pivot_mode", text=""); row.prop(props, "axis", text="")
        col.prop(props, "speed")
        
        if props.rotation_mode == 'MICRO': col.prop(props, "sweep_angle")
        if props.rotation_mode == 'INSPECT':
            col.prop(props, "osc_magnitude"); col.prop(props, "osc_speed")
            
        layout.separator()
        layout.operator("view3d.turntable_run", text="STOP" if props.running else "START TURNTABLE", icon='CANCEL' if props.running else 'PLAY')

classes = (TurntableProps, VIEW3D_OT_turntable_run, VIEW3D_PT_turntable_panel)

def register():
    for cls in classes: bpy.utils.register_class(cls)
    bpy.types.Scene.turntable_props = bpy.props.PointerProperty(type=TurntableProps)
    bpy.app.timers.register(sync_timer)
    bpy.app.handlers.load_post.append(load_post_handler)

def unregister():
    if bpy.app.timers.is_registered(sync_timer): bpy.app.timers.unregister(sync_timer)
    if load_post_handler in bpy.app.handlers.load_post: bpy.app.handlers.load_post.remove(load_post_handler)
    for cls in reversed(classes): bpy.utils.unregister_class(cls)
    del bpy.types.Scene.turntable_props

if __name__ == "__main__":
    register()