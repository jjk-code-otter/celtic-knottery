bl_info = {
    "name": "Celtic Knotter",
    "description": "",
    "author": "John Kennedy",
    "version": (0, 0, 0),
    "blender": (2, 90, 0),
    "location": "Properties > Scene",
    "warning": "", # used for warning icon and text in addons panel
    "wiki_url": "",
    "tracker_url": "",
    "category": "Development"
}

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix
from bpy.props import (FloatProperty,
                       PointerProperty,
                       )


class MyProperties(bpy.types.PropertyGroup):

    break_inset: FloatProperty(
        name = "Break Inset",
        description="Distance to inset curves at a break",
        default = 0.031,
        min = 0.01,
        max = 1.00
        )

    layer_gap: FloatProperty(
        name = "Layer gap",
        description = "Distance between ribbons at crossing points",
        default = 0.031,
        min = 0.01,
        max = 1.00
        )

    offset_from_surface: FloatProperty(
        name = "Offset from Surface",
        description = "Distance from surface to draw knot",
        default = 0.0,
        min = -1.00,
        max = 1.00
        )


def convert_to_curve(context):
    obj = bpy.context.active_object
    name = obj.name
    
    bpy.ops.object.mode_set(mode = 'OBJECT')
    bpy.ops.object.convert(target='CURVE')
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.curve.spline_type_set(type='BEZIER')
    bpy.ops.curve.select_all(action='SELECT')
    bpy.ops.curve.handle_type_set(type='ALIGNED')
    bpy.ops.object.mode_set(mode = 'OBJECT')
    
    bpy.data.objects[name].data.bevel_mode = 'OBJECT'
    bpy.data.objects[name].data.bevel_object = bpy.data.objects["BezierCircle"]
    
    bpy.ops.object.mode_set(mode = 'EDIT')
    for spline in obj.data.splines:
        spline.use_smooth = True

    bpy.ops.object.mode_set(mode = 'OBJECT')
    return


def celtic_knot(context):
    
    my_tool = context.scene.my_tool
    print(my_tool.layer_gap)
    
    obj = bpy.context.active_object
    name = obj.name
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.object.mode_set(mode = 'OBJECT')

    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)    

    bm.edges.ensure_lookup_table()
    edge = bm.edges[0]
    up = True
    edge.tag = 1

    for f in bm.faces:

        tops = []
        bottoms = []
        all = []

        for e in f.edges:
            #get edge midpoint
            midpt = sum((v.co for v in e.verts), Vector())/2.
            
            if len(e.link_faces) == 2 and not e.seam:
                # for regular internal edges with two attached faces, need 
                # two points: one high, one low
                z = sum((f2.normal for f2 in e.link_faces), Vector()).normalized()
                midpt1 = midpt + (z * my_tool.layer_gap) + (z * my_tool.offset_from_surface)
                midpt2 = midpt - (z * my_tool.layer_gap) + (z * my_tool.offset_from_surface)
            elif e.seam:
                # seams are dealt with like perimeter points, but the points are inset 
                # slightly into the face
                print(e.tag)
                vec = e.verts[0].co - e.verts[1].co
                offset_to_face = vec.cross(f.normal).normalized() * my_tool.break_inset
                z = f.normal.normalized()
                if not e.tag:
                    midpt1 = midpt + offset_to_face + (z * my_tool.offset_from_surface)
                    midpt2 = midpt + offset_to_face + (z * my_tool.offset_from_surface)
                    e.tag = True
                else:
                    midpt1 = midpt - offset_to_face + (z * my_tool.offset_from_surface)
                    midpt2 = midpt - offset_to_face + (z * my_tool.offset_from_surface)
                    e.tag = False
            else:
                # For a perimeter edge with one linked face put the two 
                # vertices at the same height so that the remove doubles will merge them
                z = sum((f2.normal for f2 in e.link_faces), Vector()).normalized()
                midpt1 = midpt + (z * my_tool.offset_from_surface)
                midpt2 = midpt + (z * my_tool.offset_from_surface)
            
            tops.append(bm.verts.new(midpt1))
            bottoms.append(bm.verts.new(midpt2))
            
        # join up the pairs of points for this face
        n = len(tops)
        for i in range(n):
            bm.edges.new((bottoms[i-1],tops[i]))

    # Remove double vertices from the knot
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.00001)  
    
    bm.to_mesh(obj.data)  
    bm.free()
    del(bm)

    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.separate(type='SELECTED')
    bpy.ops.object.mode_set(mode = 'OBJECT')
    
    bpy.ops.object.select_all(action='DESELECT')
    bpy.data.objects[name].select_set(True)
    
    return
    
class ConvertKnotToCurve(bpy.types.Operator):
    """Convert a knot to a nice curve"""
    bl_idname = "boggis.convert_celtic_knot_to_curve"
    bl_label = "Convert Knot to Curve"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        convert_to_curve(context)
        return {'FINISHED'}
    

class AddCelticKnot(bpy.types.Operator):
    """Add a celtic knot based on the polygons in a mesh"""
    bl_idname = "boggis.add_celtic_knot"
    bl_label = "Add Celtic Knot"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        celtic_knot(context)
        return {'FINISHED'}


class LayoutDemoPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Celtic"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout

        scene = context.scene

        layout.label(text="Celtic Stuff:")
    
        row = layout.row(align=True)
        row.prop(scene.my_tool, "layer_gap")
        row = layout.row(align=True)
        row.prop(scene.my_tool, "break_inset")
        row = layout.row(align=True)
        row.prop(scene.my_tool, "offset_from_surface")
    
        # Big render button
        row = layout.row()
        row.scale_y = 1.5
        row.operator("boggis.add_celtic_knot")

        row = layout.row()
        row.scale_y = 1.5
        row.operator("boggis.convert_celtic_knot_to_curve")

        

def register():
    bpy.utils.register_class(MyProperties)
    bpy.types.Scene.my_tool = PointerProperty(type=MyProperties)
    bpy.utils.register_class(AddCelticKnot)
    bpy.utils.register_class(ConvertKnotToCurve)
    bpy.utils.register_class(LayoutDemoPanel)


def unregister():
    bpy.utils.unregister_class(AddCelticKnot)
    bpy.utils.unregister_class(ConvertKnotToCurve)
    bpy.utils.unregister_class(LayoutDemoPanel)
    
    del bpy.types.Scene.my_tool

if __name__ == "__main__":
    register()
