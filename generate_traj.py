
import svgpathtools
import numpy as np
import matplotlib.pyplot as plt
import copy
import time
import yaml


RED   = (255,0,0)
GREEN = (0,255,0)
BLUE  = (0,0,255)
BLACK = (0,0,0)
MAGENTA = (255,0,255)
CYAN = (0,255,255)
YELLOW = (255,255,0)

def parse_style(string):
    attributes = string.split(';')
    items = []
    for attr in attributes:
        attr = attr.split(':')
        items.append(attr)

    out = {item[0]: item[1] for item in items}
    return out


def get_line_type(attr):
    style = attr['style']
    color_hex = parse_style(style)['stroke']

    try:

        color = svgpathtools.hex2rgb(color_hex)

        if color==BLUE:
            return "start", color

        elif color==GREEN:
            return "grasp", color
        
        elif color==RED:
            return "release", color

        elif color==YELLOW:
            return "origin", color
        
        elif color==BLACK:
            return "move_vertical", color
        
        elif color==MAGENTA:
            return "move_normal", color

        elif color==CYAN:
            return "move_tangent", color
        else:
            return None, color

    except ValueError:
        return None, None



def find_match(paths, val, tol=0.001, use_orientation=False, check_end=True):
    idx_out = None
    path_out = None

    for idx, path_dict in enumerate(paths):
        path_start = path_dict['position'][0,:]
        path_end = path_dict['position'][-1,:]

        if use_orientation:
            path_start = np.hstack((path_start,path_dict['orientation'][0]))
            path_end   = np.hstack((path_end,path_dict['orientation'][0]))

        if np.allclose(path_start, val, tol):
            idx_out = idx
            path_out = path_dict
            break

        elif np.allclose(path_end, val, tol) and check_end:
            idx_out = idx
            path_out = copy.deepcopy(path_dict)
            path_out['position'] = np.flipud(path_out['position'])
            path_out['orientation'] = np.flipud(path_out['orientation']).tolist()
            break

    return idx_out, path_out



def find_order(paths, start, tol=0.001):
    print("Finding path order...")
    num_paths = len(paths)
    path_idx = range(num_paths)
    paths_test=copy.deepcopy(paths)
    match_val = np.array(start)
    
    # Sort the paths
    paths_out =[]
    while len(paths_test)>0:

        match_idx, match_path = find_match(paths_test,match_val,tol)
        print(match_idx)
        if match_idx is not None:
            paths_out.append(match_path)
            match_val=match_path['position'][-1,:]
            #del path_idx[match_idx]
            del paths_test[match_idx]

            print(match_path['position'][0,:], match_path['orientation'][0])
            print(match_path['position'][-1,:], match_path['orientation'][-1])
        
        else:
            print()
            raise ValueError("Make sure you have a continuous trajectory drawn")


    return paths_out




# Load the image
image_file='insert_press.svg'
out_file ='../hand_arm_cbt/traj_setup/rethi/tasks/insert_press.yaml'
paths, attributes, svg_attributes = svgpathtools.svg2paths2(image_file)
plots_on=True
operating_plane = 'xz'
plane_dist = 300
unit_conversion = 0.001 # [mm to m]


# Generate a set of trajectories
trajectories=[]
special_points=[]
for path, attr in zip(paths,attributes):
    line_type ,color = get_line_type(attr)

    if line_type is not None:
        if 'move' not in line_type:
            center = np.mean([path[0].center, path[1].center])

            special_points.append({'point': [center.real, -center.imag], 'type':line_type, 'color':color})

        else:
            xy_pts=[]
            rot_pts = []
            for entity in path:
                if isinstance(entity, svgpathtools.path.Line):
                    print("LINE")
                    span = np.array([0,1])

                else:
                    print("INTERPOLATED from %s"%(type(entity)))
                    span = np.linspace(0,1,20)
                    #xy_pts_complex=entity.point(span)
                    #print(xy_pts)
                    #xy_pts.extend(xy_pts_complex)
                
                xy_pts.extend(entity.point(span))

                if 'normal' in line_type:
                    normals = entity.normal(span)
                    angles = [np.arctan2(-normal.imag, normal.real) for normal in normals]
                    rot_pts_deg = np.rad2deg(angles)
                    rot_pts.extend(rot_pts_deg.tolist())

                elif 'tangent' in line_type:
                    if isinstance(entity, svgpathtools.path.Line):
                        tangents = [entity.unit_tangent()]*len(span)
                    else:
                        tangents = entity.unit_tangent(span)
                    print(tangents)
                    angles = [np.arctan2(-tangent.imag, tangent.real) for tangent in tangents]
                    rot_pts_deg = np.rad2deg(angles)
                    rot_pts.extend(rot_pts_deg.tolist())

                else:
                    rot_pts.extend([90.0]*len(span))
            
            #print(len(xy_pts))
            x = [ele.real for ele in xy_pts]
            # extract imaginary part
            y = [-ele.imag for ele in xy_pts]

            xy_vec = np.array([x,y]).T

            trajectories.append({'orientation':rot_pts, 'position':xy_vec, 'color': color})

print(trajectories)

start_point = None
for pt in special_points:
    if pt['type'] == 'start':
        start_point = pt['point']
        break

origin = None
for pt in special_points:
    if pt['type'] == 'origin':
        origin = copy.deepcopy(pt['point'])
        break

if start_point is not None:
    trajectories = find_order(trajectories,start_point)

for traj in trajectories:
    traj['position'] = traj['position']-origin

for pt in special_points:
    pt['point'] = (np.array(pt['point'])-origin).tolist()

# Find grasps and releases
traj_group_idx = [0]
traj_group_end_type=[False]
for pt in special_points:
    if 'grasp' in pt['type'] or 'release' in pt['type']:
        pt_idx, _ = find_match(trajectories,pt['point'], check_end=False)
        traj_group_idx.append(pt_idx)
        traj_group_end_type.append(pt['type'])

traj_groups=[]
for idx in range(len(traj_group_idx)-1):
    last_idx = traj_group_idx[idx]
    curr_idx = traj_group_idx[idx+1]
    traj_groups.append(trajectories[last_idx:curr_idx])
    print(last_idx, curr_idx)

traj_groups.append(trajectories[curr_idx:len(trajectories)])
print(curr_idx,len(trajectories))

# Make nice plots
if plots_on:
    fig = plt.figure()
    plt.ion()
    ax=plt.gca()
    ax.set_aspect('equal', 'box')
    plt.title("Plane Distance: %0.3f(m)"%(plane_dist/1000.0))
    if operating_plane=='xy':
        plt.xlabel('x')
        plt.ylabel('y')

    if operating_plane=='xz':
        plt.xlabel('x')
        plt.ylabel('z')

    if operating_plane=='yz':
        plt.xlabel('y')
        plt.ylabel('z')
    plt.show()
    fig.canvas.draw()
    time.sleep(0.3)

    for traj_group in traj_groups:
        for traj in traj_group:
            plt.plot(traj['position'][:,0],traj['position'][:,1], color=np.array(traj['color'])/255, linewidth=2.5)
            plt.plot(traj['position'][0,0] ,traj['position'][0,1], '.',color=np.array(traj['color'])/255, markersize=4, markeredgewidth=2.5)
        
        fig.canvas.draw()
        time.sleep(0.3)
        

    for pt in special_points:
        plt.plot(pt['point'][0],pt['point'][1], 'o',color=np.array(pt['color'])/255, markersize=15, markerfacecolor='none', markeredgewidth=2.5)


    plt.ioff()
    plt.show()

for traj_group in traj_groups:
    for traj in traj_group:
        traj['position'][:,0] = -traj['position'][:,0]


# Format trajectories
trajectory_fmt = {}
sequence=[]
traj_idx = 0
for group_idx, traj_group in enumerate(traj_groups):
    traf_curr_fmt = []
    for traj in traj_group:
        for pos, ori in zip(traj['position'].tolist(), traj['orientation']):

            if operating_plane=='xy':
                pos_out= pos
                pos_out.insert(2,plane_dist)
                ori_out = [0,0, ori]

            if operating_plane=='xz':
                pos_out= pos
                pos_out.insert(1,plane_dist)
                ori_out = [0,ori,0]

            if operating_plane=='yz':
                pos_out= pos
                pos_out.insert(0,plane_dist)
                ori_out = [ori,0,0]


            pos_out=(np.array(pos_out)*unit_conversion).tolist()
                
                
                
            traf_curr_fmt.append({'position': pos_out, 'orientation': ori_out})

    traj_name='traj_group_%02d'%(traj_idx)
    trajectory_fmt[traj_name] = traf_curr_fmt
    
    sequence.append({'arm':False, 'hand':traj_group_end_type[group_idx], 'servo':False})
    sequence.append({'arm':traj_name, 'hand':False, 'servo':False})

    traj_idx+=1

traj_def_out = {'sequence':sequence, 'arm':trajectory_fmt}

with open(out_file,'w') as f:
    yaml.dump(traj_def_out, f, default_flow_style=None)