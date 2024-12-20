# from https://github.com/xlang-ai/OSWorld/blob/97b567a287e036744f6868957fabf7d38f072bf2/mm_agents/agent.py#L1



import base64
import json
import logging
import os
import re
import time
import uuid
import xml.etree.ElementTree as ET
import tiktoken
from io import BytesIO
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont
import requests

def find_leaf_nodes(xlm_file_str):
    if not xlm_file_str:
        return []

    root = ET.fromstring(xlm_file_str)

    # Recursive function to traverse the XML tree and collect leaf nodes
    def collect_leaf_nodes(node, leaf_nodes):
        # If the node has no children, it is a leaf node, add it to the list
        if not list(node):
            leaf_nodes.append(node)
        # If the node has children, recurse on each child
        for child in node:
            collect_leaf_nodes(child, leaf_nodes)

    # List to hold all leaf nodes
    leaf_nodes = []
    collect_leaf_nodes(root, leaf_nodes)
    return leaf_nodes

state_ns = "uri:deskat:state.at-spi.gnome.org"
component_ns = "uri:deskat:component.at-spi.gnome.org"
def judge_node(node: ET, platform="ubuntu", check_image=False) -> bool:
    if platform == "ubuntu":
        _state_ns = state_ns_ubuntu
        _component_ns = component_ns_ubuntu
    elif platform == "windows":
        _state_ns = state_ns_windows
        _component_ns = component_ns_windows
    else:
        raise ValueError("Invalid platform, must be 'ubuntu' or 'windows'")

    keeps: bool = node.tag.startswith("document") \
                  or node.tag.endswith("item") \
                  or node.tag.endswith("button") \
                  or node.tag.endswith("heading") \
                  or node.tag.endswith("label") \
                  or node.tag.endswith("scrollbar") \
                  or node.tag.endswith("searchbox") \
                  or node.tag.endswith("textbox") \
                  or node.tag.endswith("link") \
                  or node.tag.endswith("tabelement") \
                  or node.tag.endswith("textfield") \
                  or node.tag.endswith("textarea") \
                  or node.tag.endswith("menu") \
                  or node.tag in {"alert", "canvas", "check-box"
                      , "combo-box", "entry", "icon"
                      , "image", "paragraph", "scroll-bar"
                      , "section", "slider", "static"
                      , "table-cell", "terminal", "text"
                      , "netuiribbontab", "start", "trayclockwclass"
                      , "traydummysearchcontrol", "uiimage", "uiproperty"
                      , "uiribboncommandbar"
                                  }
    keeps = keeps and (
            platform == "ubuntu"
            and node.get("{{{:}}}showing".format(_state_ns), "false") == "true"
            and node.get("{{{:}}}visible".format(_state_ns), "false") == "true"
            or platform == "windows"
            and node.get("{{{:}}}visible".format(_state_ns), "false") == "true"
    ) \
            and (
                    node.get("{{{:}}}enabled".format(_state_ns), "false") == "true"
                    or node.get("{{{:}}}editable".format(_state_ns), "false") == "true"
                    or node.get("{{{:}}}expandable".format(_state_ns), "false") == "true"
                    or node.get("{{{:}}}checkable".format(_state_ns), "false") == "true"
            ) \
            and (
                    node.get("name", "") != "" or node.text is not None and len(node.text) > 0 \
                    or check_image and node.get("image", "false") == "true"
            )

    coordinates: Tuple[int, int] = eval(node.get("{{{:}}}screencoord".format(_component_ns), "(-1, -1)"))
    sizes: Tuple[int, int] = eval(node.get("{{{:}}}size".format(_component_ns), "(-1, -1)"))
    keeps = keeps and coordinates[0] >= 0 and coordinates[1] >= 0 and sizes[0] > 0 and sizes[1] > 0
    return keeps

def filter_nodes(root: ET, platform="ubuntu", check_image=False):
    filtered_nodes = []

    for node in root.iter():
        if judge_node(node, platform, check_image):
            filtered_nodes.append(node)
            #print(ET.tostring(node, encoding="unicode"))

    return filtered_nodes


def draw_bounding_boxes(nodes, image_file_path, output_image_file_path, down_sampling_ratio=1.0):
    # Load the screenshot image
    image = Image.open(image_file_path)
    if float(down_sampling_ratio) != 1.0:
        image = image.resize((int(image.size[0] * down_sampling_ratio), int(image.size[1] * down_sampling_ratio)))
    draw = ImageDraw.Draw(image)
    marks = []
    drew_nodes = []
    text_informations: List[str] = ["index\ttag\tname\ttext"]

    try:
        # Adjust the path to the font file you have or use a default one
        font = ImageFont.truetype("arial.ttf", 15)
    except IOError:
        # Fallback to a basic font if the specified font can't be loaded
        font = ImageFont.load_default()

    index = 1

    # Loop over all the visible nodes and draw their bounding boxes
    for _node in nodes:
        coords_str = _node.attrib.get('{uri:deskat:component.at-spi.gnome.org}screencoord')
        size_str = _node.attrib.get('{uri:deskat:component.at-spi.gnome.org}size')

        if coords_str and size_str:
            try:
                # Parse the coordinates and size from the strings
                coords = tuple(map(int, coords_str.strip('()').split(', ')))
                size = tuple(map(int, size_str.strip('()').split(', ')))

                import copy
                original_coords = copy.deepcopy(coords)
                original_size = copy.deepcopy(size)

                if float(down_sampling_ratio) != 1.0:
                    # Downsample the coordinates and size
                    coords = tuple(int(coord * down_sampling_ratio) for coord in coords)
                    size = tuple(int(s * down_sampling_ratio) for s in size)

                # Check for negative sizes
                if size[0] <= 0 or size[1] <= 0:
                    raise ValueError(f"Size must be positive, got: {size}")

                # Calculate the bottom-right corner of the bounding box
                bottom_right = (coords[0] + size[0], coords[1] + size[1])

                # Check that bottom_right > coords (x1 >= x0, y1 >= y0)
                if bottom_right[0] < coords[0] or bottom_right[1] < coords[1]:
                    raise ValueError(f"Invalid coordinates or size, coords: {coords}, size: {size}")

                # Check if the area only contains one color
                cropped_image = image.crop((*coords, *bottom_right))
                if len(set(list(cropped_image.getdata()))) == 1:
                    continue

                # Draw rectangle on image
                draw.rectangle([coords, bottom_right], outline="red", width=1)

                # Draw index number at the bottom left of the bounding box with black background
                text_position = (coords[0], bottom_right[1])  # Adjust Y to be above the bottom right
                text_bbox: Tuple[int, int ,int ,int] = draw.textbbox(text_position, str(index), font=font, anchor="lb")
                #offset: int = bottom_right[1]-text_bbox[3]
                #text_bbox = (text_bbox[0], text_bbox[1]+offset, text_bbox[2], text_bbox[3]+offset)

                #draw.rectangle([text_position, (text_position[0] + 25, text_position[1] + 18)], fill='black')
                draw.rectangle(text_bbox, fill='black')
                draw.text(text_position, str(index), font=font, anchor="lb", fill="white")

                # each mark is an x, y, w, h tuple
                marks.append([original_coords[0], original_coords[1], original_size[0], original_size[1]])
                drew_nodes.append(_node)

                if _node.text:
                    node_text = ( _node.text if '"' not in _node.text\
                             else '"{:}"'.format(_node.text.replace('"', '""'))
                                )
                elif _node.get("{uri:deskat:uia.windows.microsoft.org}class", "").endswith("EditWrapper") \
                        and _node.get("{uri:deskat:value.at-spi.gnome.org}value"):
                    node_text: str = _node.get("{uri:deskat:value.at-spi.gnome.org}value")
                    node_text = (node_text if '"' not in node_text\
                             else '"{:}"'.format(node_text.replace('"', '""'))
                                )
                else:
                    node_text = '""'
                text_information: str = "{:d}\t{:}\t{:}\t{:}"\
                                            .format( index, _node.tag
                                                   , _node.get("name", "")
                                                   , node_text
                                                   )
                text_informations.append(text_information)

                index += 1

            except ValueError:
                pass

    # Save the result
    image.save(output_image_file_path)
    return marks, drew_nodes, "\n".join(text_informations)


def print_nodes_with_indent(nodes, indent=0):
    for node in nodes:
        print(' ' * indent, node.tag, node.attrib)
        print_nodes_with_indent(node, indent + 2)


# Function to encode the image
def encode_image(image_content):
    return base64.b64encode(image_content).decode('utf-8')


attributes_ns_ubuntu = "https://accessibility.windows.example.org/ns/attributes"
attributes_ns_windows = "https://accessibility.windows.example.org/ns/attributes"
state_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/state"
state_ns_windows = "https://accessibility.windows.example.org/ns/state"
component_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/component"
component_ns_windows = "https://accessibility.windows.example.org/ns/component"
value_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/value"
value_ns_windows = "https://accessibility.windows.example.org/ns/value"
class_ns_windows = "https://accessibility.windows.example.org/ns/class"
# More namespaces defined in OSWorld, please check desktop_env/server/main.py

def linearize_accessibility_tree(accessibility_tree, platform="ubuntu"):

    if platform == "ubuntu":
        _attributes_ns = attributes_ns_ubuntu
        _state_ns = state_ns_ubuntu
        _component_ns = component_ns_ubuntu
        _value_ns = value_ns_ubuntu
    elif platform == "windows":
        _attributes_ns = attributes_ns_windows
        _state_ns = state_ns_windows
        _component_ns = component_ns_windows
        _value_ns = value_ns_windows
    else:
        raise ValueError("Invalid platform, must be 'ubuntu' or 'windows'")

    filtered_nodes = filter_nodes(ET.fromstring(accessibility_tree), platform)
    linearized_accessibility_tree = ["tag\tname\ttext\tclass\tdescription\tposition (top-left x&y)\tsize (w&h)"]

    # Linearize the accessibility tree nodes into a table format
    for node in filtered_nodes:
        if node.text:
            text = (
                node.text if '"' not in node.text \
                    else '"{:}"'.format(node.text.replace('"', '""'))
            )

        elif node.get("{{{:}}}class".format(class_ns_windows), "").endswith("EditWrapper") \
                and node.get("{{{:}}}value".format(_value_ns)):
            node_text = node.get("{{{:}}}value".format(_value_ns), "")
            text = (node_text if '"' not in node_text \
                        else '"{:}"'.format(node_text.replace('"', '""'))
                    )
        else:
            text = '""'

        linearized_accessibility_tree.append(
            "{:}\t{:}\t{:}\t{:}\t{:}".format(
                node.tag, node.get("name", ""),
                text,
                node.get('{{{:}}}screencoord'.format(_component_ns), ""),
                node.get('{{{:}}}size'.format(_component_ns), "")
            )
        )

    return "\n".join(linearized_accessibility_tree)

# def linearize_accessibility_tree(accessibility_tree, platform="ubuntu"):
#     # leaf_nodes = find_leaf_nodes(accessibility_tree)
#     filtered_nodes = filter_nodes(ET.fromstring(accessibility_tree), platform)

#     linearized_accessibility_tree = ["tag\tname\ttext\tposition (top-left x&y)\tsize (w&h)"]
#     # Linearize the accessibility tree nodes into a table format

#     for node in filtered_nodes:
#         # linearized_accessibility_tree += node.tag + "\t"
#         # linearized_accessibility_tree += node.attrib.get('name') + "\t"
#         if node.text:
#             text = (node.text if '"' not in node.text \
#                         else '"{:}"'.format(node.text.replace('"', '""'))
#                     )
#         elif node.get("{uri:deskat:uia.windows.microsoft.org}class", "").endswith("EditWrapper") \
#                 and node.get("{uri:deskat:value.at-spi.gnome.org}value"):
#             text: str = node.get("{uri:deskat:value.at-spi.gnome.org}value")
#             text = (text if '"' not in text \
#                         else '"{:}"'.format(text.replace('"', '""'))
#                     )
#         else:
#             text = '""'
#         # linearized_accessibility_tree += node.attrib.get(
#         # , "") + "\t"
#         # linearized_accessibility_tree += node.attrib.get('{uri:deskat:component.at-spi.gnome.org}size', "") + "\n"
#         linearized_accessibility_tree.append(
#             "{:}\t{:}\t{:}\t{:}\t{:}".format(
#                 node.tag, node.get("name", ""), text
#                 , node.get('{uri:deskat:component.at-spi.gnome.org}screencoord', "")
#                 , node.get('{uri:deskat:component.at-spi.gnome.org}size', "")
#             )
#         )

#     return "\n".join(linearized_accessibility_tree)

def parse_ui_data_dict(data):
    # 将输入字符串分割成单独的行
    lines = data.strip().split('\n')
    
    # 初始化一个字典来存储结果
    ui_dict = {}
    
    # 遍历数据的每一行，跳过标题行
    for line in lines[1:]:
        # 分割每一行的字段，这里假设字段之间由制表符'\t'分隔
        parts = line.split('\t')
        if len(parts) < 4:
            continue
        # 获取name和position字段
        name = parts[1].strip()
        position = parts[3].strip('()')  # 移除位置坐标周围的括号
        
        # 将name和position添加到字典中
        if name:  # 确保name非空
            x,y = position.replace('(', '').replace(')', '').split(',')
            new_x = int(x) + 10
            new_y = int(y) + 10
            # 格式化回字符串
            ui_dict[name] = f'({new_x}, {new_y})'
    return json.dumps(ui_dict)


def tag_screenshot(screenshot, accessibility_tree, platform="ubuntu"):
    # Creat a tmp file to store the screenshot in random name
    uuid_str = str(uuid.uuid4())
    os.makedirs("tmp/images", exist_ok=True)
    tagged_screenshot_file_path = os.path.join("tmp/images", uuid_str + ".png")
    # nodes = filter_nodes(find_leaf_nodes(accessibility_tree))
    nodes = filter_nodes(ET.fromstring(accessibility_tree), platform=platform, check_image=True)
    # Make tag screenshot
    marks, drew_nodes, element_list = draw_bounding_boxes(nodes, screenshot, tagged_screenshot_file_path)

    return marks, drew_nodes, tagged_screenshot_file_path, element_list


def trim_accessibility_tree(linearized_accessibility_tree, max_tokens):
    enc = tiktoken.encoding_for_model("gpt-4")
    tokens = enc.encode(linearized_accessibility_tree)
    if len(tokens) > max_tokens:
        linearized_accessibility_tree = enc.decode(tokens[:max_tokens])
        linearized_accessibility_tree += "[...]\n"
    return linearized_accessibility_tree


def ocr(base64_image, ui_dict):


    request_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate"
    request_url = "https://aip.baidubce.com/rest/2.0/ocr/v1/general"


    params = {"image": base64_image, 'probability': 'true'}
    access_token = '24.3e11a3856ca146627d4e7c4555a384d8.2592000.1726904372.282335-109280435'
    request_url = request_url + "?access_token=" + access_token
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    response = requests.post(request_url, data=params, headers=headers)
    if not response:
        return ui_dict
    
    dict_ = json.loads(ui_dict)

    data = response.json()['words_result']

    for item in data:
        if item['probability']['average'] < 0.85:
            continue
        location = item['location']
        top = location['top']
        left = location['left']
        width = location['width']
        height = location['height']
        x = left + width // 2
        y = top + height // 2
        
        dict_[item['words']] = f'({x}, {y})'

    ui_dict = json.loads(ui_dict)

    ui_dict = ui_dict | dict_

    return json.dumps(ui_dict)

def parse_obs(obs, observation_type, ocr_type=True):
    a11y_tree_max_tokens = 3000
    if observation_type in ["screenshot", "screenshot_a11y_tree"]:
        base64_image = encode_image(obs["screenshot"])
        linearized_accessibility_tree = parse_ui_data_dict(linearize_accessibility_tree(accessibility_tree=obs["accessibility_tree"]
                                                                        )) if observation_type == "screenshot_a11y_tree" else None

        if ocr_type:
            linearized_accessibility_tree = ocr(base64_image, linearized_accessibility_tree)

        if linearized_accessibility_tree:
            linearized_accessibility_tree = trim_accessibility_tree(linearized_accessibility_tree,
                                                                    a11y_tree_max_tokens)  

        obs["base64_image"] = base64_image
        obs["linearized_accessibility_tree"] = linearized_accessibility_tree


    
    elif observation_type == "a11y_tree":
        linearized_accessibility_tree = parse_ui_data_dict(linearize_accessibility_tree(accessibility_tree=obs["accessibility_tree"]
                                                                        ))
        if linearized_accessibility_tree:
            linearized_accessibility_tree = trim_accessibility_tree(linearized_accessibility_tree,
                                                                    a11y_tree_max_tokens)
        obs["linearized_accessibility_tree"] = linearized_accessibility_tree
    
    elif observation_type == "som":
        # Add som to the screenshot
        masks, drew_nodes, tagged_screenshot, linearized_accessibility_tree = tag_screenshot(obs["screenshot"], obs[
            "accessibility_tree"], platform)
        base64_image = encode_image(tagged_screenshot)

        if linearized_accessibility_tree:
            linearized_accessibility_tree = trim_accessibility_tree(linearized_accessibility_tree,
                                                                    a11y_tree_max_tokens)
        obs["base64_image"] = base64_image
        obs["linearized_accessibility_tree"] = linearized_accessibility_tree
    
    return obs
