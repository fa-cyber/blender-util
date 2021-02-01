from functools import partial
import bpy



NURBS_GUIDE_WEIGHT = 1
NUM_SEGS = 5
SEG_PACING = 10

assert NUM_SEGS >= 3

def make_path(collection, name, segments):
    path = bpy.data.curves.new("curve", "CURVE")
    spline = path.splines.new(type="NURBS")
    spline.points.add(segments)
    for point in spline.points:
        point.co[-1] = NURBS_GUIDE_WEIGHT
    obj = bpy.data.objects.new(name, path)
    collection.objects.link(obj)
    return obj
    
def make_empty(collection, name):
    obj = bpy.data.objects.new(name, None)
    collection.objects.link(obj)
    return obj

def make_hook_target(collection, guide_path, inter_path, i):
    hook = inter_path.modifiers.new("Hook", "HOOK")
    hook.vertex_indices_set((i,))
    hook_target = make_empty(collection, "HookTarget")
    hook.object = hook_target
    
    fpc = hook_target.constraints.new("FOLLOW_PATH")
    fpc.target = guide_path
    fpc.use_curve_follow = True
    fpc.forward_axis = "FORWARD_Y"
    fpc.up_axis = "UP_Z"
    
    return hook_target
    
def get_curve_length(curve_obj):
    return sum(spline.calc_length() for spline in curve_obj.data.splines)


def calc_sec_offset(id, guide_obj):
    print(f"{id} updated")
    frames = guide_obj.data.path_duration
    length = get_curve_length(guide_obj)
    print("(100/frames)", (100/frames))
    print("frames", frames)
    print("(100/length)", (100/length))
    print("length", length)
    print("pacing", (100/frames)*(100/length)*SEG_PACING)
    return (100/frames)*(100/length)*SEG_PACING

def main():

    collection = bpy.data.collections.new("SnakeRailSystem")
    id = collection.name.replace(".", "")
    bpy.context.scene.collection.children.link(collection)

    guide_path = make_path(collection, "GuidePath", 5)
    guide_path.data.use_path = True
    d = guide_path.data.driver_add("eval_time")
    d.driver.expression = "frame"
    for i, point in enumerate(guide_path.data.splines[0].points, -1):
        i = i if i > 0 else 0
        point.co[1] = i*1/3*100
        point.co[-1] = 1
    
    inter_path = make_path(collection, "InterPath", NUM_SEGS-1)


    hooks = tuple(make_hook_target(collection, guide_path, inter_path, i)
                    for i, point in enumerate(inter_path.data.splines[0].points))
                    
    # Only number 2 has the math
    sec = hooks[1]
    sec.name = "ManuallyUpdateDriverDependenciesForMe"
    offset = sec.constraints[0].driver_add("offset")
    customFuncName = f"{id}_sec_offset"     
    bpy.app.driver_namespace[customFuncName] = partial(calc_sec_offset, id, guide_path)
    offset.driver.expression = f"{customFuncName}()"
    
    # The rest follow 2 at different increments of pacing
    for i, hook in enumerate(hooks[2:], 2):
        offset = hook.constraints[0].driver_add("offset")
        parent = offset.driver.variables.new()
        parent.name = "var"
        parent.targets[0].id = sec
        parent.targets[0].data_path = "constraints[\"Follow Path\"].offset"
        offset.driver.expression = f"var * {i}"
        


main()
