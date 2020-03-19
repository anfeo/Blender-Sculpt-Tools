bl_info = {
    "name": "Sculpt Tools",
    "author": "Alfonso Annarumma",
    "version": (1, 2),
    "blender": (2, 80, 0),
    "location": "Header > Show Tools Settings > Sculpt Tools",
    "description": "Adds a new Mesh Object",
    "warning": "",
    "wiki_url": "",
    "category": "Sculpt",
}


import bpy
import bmesh
import math
import mathutils
from bpy.types import Menu, Panel, UIList, PropertyGroup, Operator
from bpy_extras.object_utils import AddObjectHelper
from bpy.props import (
        StringProperty,
        BoolProperty,
        FloatProperty,
        IntProperty,
        CollectionProperty,
        BoolVectorProperty,
        PointerProperty,
        EnumProperty,
        )
class SCENE_PG_Sculpt_Tools(PropertyGroup):
    subsurf: IntProperty(
            name="Subdivision",
            default=2,
            description="Subdivision Surface level"
            )
    
    presub: IntProperty(
            name="PreSubdivision",
            default=0,
            description="Subdivision Surface first of Skin Modifier (only for skin convertor)"
            )
    
    distance: FloatProperty(
            name="Clean Limit",
            default=0.001,
            description="Distance from vertices to collpse to clean surface"
            )

def cone_between(x1, y1, z1, x2, y2, z2, r1,r2):
    
  dx = x2 - x1
  dy = y2 - y1
  dz = z2 - z1    
  dist = math.sqrt(dx**2 + dy**2 + dz**2)

  bpy.ops.mesh.primitive_cone_add(
      radius1 = r1, 
      radius2 = r2, 
      depth = dist,
      location = (dx/2 + x1, dy/2 + y1, dz/2 + z1)   
  ) 

  phi = math.atan2(dy, dx) 
  theta = math.acos(dz/dist) 

  bpy.context.object.rotation_euler[1] = theta 
  bpy.context.object.rotation_euler[2] = phi
  
 



def convert_envelope(arm, context):
    coords = []
    obs = []
    prop = context.scene.sculpttools
    for bone in arm.data.bones:      
        
        x1,y1,z1 = bone.tail_local+arm.location
        r1 = bone.tail_radius
        coord1 = (x1,y1,z1,r1)
        if coord1 not in coords:
            coords.append(coord1)
        
            bpy.ops.mesh.primitive_uv_sphere_add(
            radius = r1,
            location = bone.tail_local+arm.location,
            
            )
            obs.append(context.object.name)

        x2,y2,z2 = bone.head_local+arm.location
        r2 = bone.head_radius
        coord2 = (x2,y2,z2,r2)
        if coord2 not in coords:
            coords.append(coord2)
            bpy.ops.mesh.primitive_uv_sphere_add(
            radius = r2,
            location = bone.head_local+arm.location
            )
            obs.append(context.object.name)
        cone_between(x1, y1, z1, x2, y2, z2, r1,r2)

        obs.append(context.object.name)
 
    for ob in obs:
        bpy.context.collection.objects[ob].select_set(True)
        #print(ob)
    bpy.ops.object.join()
    
    obj = context.object
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    cursor = context.scene.cursor.location
    context.scene.cursor.location = arm.location
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    context.scene.cursor.location = cursor
    mesh = obj.data
    #_mesh = RemoveDoubles(mesh,prop.distance)
    obj.data = mesh
    #bpy.data.meshes.remove(mesh)
    
    #int(obj.data.name)
    #print(arm.envelope_ID)
    return obj

def RemoveDoubles (mesh,distance):
    
    bm = bmesh.new()   
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=distance)
    bm.to_mesh(mesh)
    mesh.update()
    bm.clear()

    bm.free()
    return mesh
def convert_skin(context):
    """
    This function takes inputs and returns vertex and face arrays.
    no actual mesh data creation is done here.
    """
    verts = []
    edges = []
    arm = context.object
    bones = arm.data.bones
    radius = []
    
    for b in bones:
        v1 = b.head_local
        r1 = b.head_radius
        v2 = b.tail_local
        r2 = b.tail_radius
        
        verts.append(v1)
        
        verts.append(v2)
        radius.append(r1)
        radius.append(r2)
        #print(verts) 
        edges.append( (verts.index(verts[-1]),verts.index(verts[-2])))


    return verts, edges, radius


from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
)



class OBJECT_OT_AddEnvelope(bpy.types.Operator):
    """Add a simple Bone with Envelope view in Edit Mode"""
    bl_idname = "object.addenvelope"
    bl_label = "Add Envelope"
    bl_options = {'REGISTER', 'UNDO'}

    

    def execute(self, context):
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.armature_add()
        
        ob = context.object

        ob.data.display_type = 'ENVELOPE'
        ob.show_in_front = True
        bpy.ops.object.mode_set(mode='EDIT')
        
        return {'FINISHED'}
    
class OBJECT_OT_ConvertEnvelope(bpy.types.Operator):
    """Convert Envelope Armature to Skin Object"""
    bl_idname = "object.convertenvelope"
    bl_label = "Convert Envelope"
    bl_options = {'REGISTER', 'UNDO'}
    
    update : BoolProperty(default=False)
    envelope : BoolProperty(default=False)
    
    
    # generic transform props
    align_items = (
        ('WORLD', "World", "Align the new object to the world"),
        ('VIEW', "View", "Align the new object to the view"),
        ('CURSOR', "3D Cursor", "Use the 3D cursor orientation for the new object")
    )
    align: EnumProperty(
        name="Align",
        items=align_items,
        default='WORLD',
        update=AddObjectHelper.align_update_callback,
    )
    location: FloatVectorProperty(
        name="Location",
        subtype='TRANSLATION',
    )
    rotation: FloatVectorProperty(
        name="Rotation",
        subtype='EULER',
    )

    def execute(self, context):
        prop = context.scene.sculpttools
        arm = context.object
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        cursor = context.scene.cursor.location
        context.scene.cursor.location = context.object.location
        arm.display_type = 'BOUNDS'
        
        if self.envelope:            
            if not self.update:
                convert_envelope(arm, context)
                obj = context.object
                arm.envelope_ID = obj.name
                bev = obj.modifiers.new("Bevel", 'BEVEL')
                bev.offset_type = 'OFFSET'
                bev.limit_method = 'ANGLE'
                bev.segments = 2
                bev.angle_limit = math.radians(70)
                sub = obj.modifiers.new("Subsurf", 'SUBSURF')
                sub.levels = prop.subsurf
            else:
                if 'EDIT' in context.mode:
                    bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.mode_set(mode='OBJECT')
                
                obj = convert_envelope(arm, context)
                
                _obj = context.collection.objects[arm.envelope_ID]
                _mesh = _obj.data
                
                _obj.data = obj.data
                
                context.collection.objects.unlink(obj)
                bpy.data.meshes.remove(_mesh)
                #bpy.data.meshes.update()
                context.view_layer.objects.active = arm
                bpy.ops.object.mode_set(mode='EDIT')
            return {'FINISHED'}
        
        else:
            verts_loc, edges, radius = convert_skin(
                context
            )

            mesh = bpy.data.meshes.new("Skin")

            bm = bmesh.new()

            for v_co in verts_loc:
                bm.verts.new(v_co)

            bm.verts.ensure_lookup_table()
            for e_idx in edges:
                bm.edges.new([bm.verts[i] for i in e_idx])

            bm.to_mesh(mesh)
            mesh.update()
            if not self.update:
                # add the mesh as an object into the scene with this utility module
                from bpy_extras import object_utils
                object_utils.object_data_add(context, mesh, operator=self)
                
                context.scene.cursor.location = cursor
                
                obj = context.object
                arm.envelope_ID = obj.name
                mod = obj.modifiers.new("Subdiv",'SUBSURF')
                mod.levels = prop.presub
                obj.modifiers.new("Skin",'SKIN')
            else:
                obj = context.scene.objects[arm.envelope_ID]
                _mesh = obj.data
                obj.data = mesh
                bpy.data.meshes.remove(_mesh)
                context.view_layer.objects.active = obj
                bpy.ops.mesh.customdata_skin_add()
                context.scene.cursor.location = cursor
                context.view_layer.objects.active = arm
            i = 0
            for r in radius:
                obj.data.skin_vertices[0].data[i].radius = r,r
                
                i+=1        
            
            mesh = obj.data
            mesh_ = RemoveDoubles (mesh, prop.distance)
            #mesh_ = mesh
            
            obj.data = mesh_
            if not self.update:
                mod = obj.modifiers.new("Subdiv",'SUBSURF')
                mod.levels = prop.subsurf
                return {'FINISHED'}
            else:
                bpy.ops.object.mode_set(mode='EDIT')
            return {'FINISHED'}

class SCULPT_PT_Extra_tools(Panel):
    bl_label = "Sculpt Tools"
    bl_idname = "SCULPT_MT_Extra_tools"
    bl_region_type = "WINDOW"
    bl_space_type = "VIEW_3D"

    def draw(self, context):
        prop = context.scene.sculpttools
        obj = context.object
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.
        row = layout.row(align=True)
        row.operator("object.addenvelope",
                        icon='OUTLINER_OB_ARMATURE',
                        text="Add Envelope")
        row = layout.row(align=True)
        row.prop(prop, "subsurf")
        row = layout.row(align=True)
        row.prop(prop, "presub")
        row = layout.row(align=True)
        row.prop(prop, "distance")
        row = layout.row(align=True)
        row.separator()
        row = layout.row(align=True)
        col = row.column(align=True)
        if obj:
            if obj.type == 'ARMATURE':
                env = col.operator("object.convertenvelope",
                                icon='MOD_SKIN',
                                text="Convert to Skin")
                env.update = False
                env.envelope = False
                
                if obj.envelope_ID != "":
                    if obj.envelope_ID in context.scene.objects:
                        env = col.operator("object.convertenvelope",
                                        icon='MOD_SKIN',
                                        text="Update")
                        env.update = True
                        env.envelope = False
                        
                col = row.column(align=True)
                env = col.operator("object.convertenvelope",
                                icon='MOD_SKIN',
                                text="Convert to Envelope")
                env.envelope = True
                env.update = False
                              
                if obj.envelope_ID != "":
                    if obj.envelope_ID in context.scene.objects:
                        env =col.operator("object.convertenvelope",
                                        icon='MOD_SKIN',
                                        text="Update")
                        env.update = True
                        env.envelope = True
            else:
                row.label(text="Select or Add Armature/Envelope to make Skin")

classes = (
    SCENE_PG_Sculpt_Tools,
    OBJECT_OT_ConvertEnvelope,
    OBJECT_OT_AddEnvelope,
    SCULPT_PT_Extra_tools,
    )



def menu_func(self, context):
    
    layout = self.layout
    layout.popover("SCULPT_MT_Extra_tools")

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.sculpttools = PointerProperty(type=SCENE_PG_Sculpt_Tools)
    bpy.types.Object.envelope_ID = StringProperty(default="")
    bpy.types.VIEW3D_HT_tool_header.append(menu_func)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    bpy.types.VIEW3D_HT_tool_header.remove(menu_func)
    del bpy.types.Scene.sculpttools
if __name__ == "__main__":
    register()

    # test call
    #bpy.ops.mesh.primitive_box_add()
