#from svgpathtools import svg2paths2
import svgpathtools
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib.pyplot as plt
import copy


RED   = (255,0,0)
GREEN = (0,255,0)
BLUE  = (0,0,255)
BLACK = (0,0,0)
MAGENTA = (255,0,255)
CYAN = (0,255,255)

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


def find_order(paths, start):
    # Find the first segment
    num_paths = len(paths)
    paths_test=copy.deepcopy(paths)

    idx_out = []
    paths_out =[]
    for idx, path in enumerate(paths):
        if path[0]==start:
            idx_out.append(idx)
            paths_out.append(path)
            del paths_test[idx]
            break

        elif path[-1]==start:
            paths_out.append(reversed(path))
            idx_out.append(idx)
            del paths_test[idx]
            break


    # Generate test vars
    points=[]
    for idx in range(num_paths):
        points.append({'start':paths[idx][0], 'end':paths[idx][-1]})


    # Sort the rest of the segments
    for idx in range(num_paths-1):
        points to match = idx_out[idx]

        for idx_test, path_test in enumerate(paths_test):

    return idx_out


paths, attributes, svg_attributes = svgpathtools.svg2paths2('test_traj.svg')
special_points=[]

fig = plt.figure()

trajectories=[]
for path, attr in zip(paths,attributes):
    print("")
    line_type ,color = get_line_type(attr)
    print(color)

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
                    angles = [np.arctan2(normal.imag, normal.real) for normal in normals]
                    rot_pts_deg = np.rad2deg(angles)
                    rot_pts.extend(rot_pts_deg)

                elif 'tangent' in line_type:
                    if isinstance(entity, svgpathtools.path.Line):
                        tangents = [entity.unit_tangent()]*len(span)
                    else:
                        tangents = entity.unit_tangent(span)
                    print(tangents)
                    angles = [np.arctan2(tangent.imag, tangent.real) for tangent in tangents]
                    rot_pts_deg = np.rad2deg(angles)
                    rot_pts.extend(rot_pts_deg)

                else:
                    rot_pts.extend([-90.0]*len(span))
            
            #print(len(xy_pts))
            x = [ele.real for ele in xy_pts]
            # extract imaginary part
            y = [-ele.imag for ele in xy_pts]

            xy_vec = np.array([x,y]).T

            plt.plot(x,y, color=np.array(color)/255, linewidth=2.5)

            print(rot_pts)

            trajectories.append({'orientation':rot_pts_deg, 'position':xy_vec})

trajectories

for pt in special_points:
    plt.plot(pt['point'][0],pt['point'][1], 'o',color=np.array(pt['color'])/255, markersize=15, markerfacecolor='none', markeredgewidth=2.5)
ax=plt.gca()
ax.set_aspect('equal', 'box')
plt.show()