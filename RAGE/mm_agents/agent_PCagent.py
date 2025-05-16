import base64
import json
import logging
import os
import re
import tempfile
import time
import xml.etree.ElementTree as ET
from http import HTTPStatus
from io import BytesIO
from typing import Dict, List
import os
import time
import copy
import torch
import shutil
from PIL import Image, ImageDraw
import io
from mm_agents.PCAgent.api import inference_chat
from mm_agents.PCAgent.text_localization import ocr
from mm_agents.PCAgent.icon_localization import det
from mm_agents.PCAgent.prompt import get_reflect_prompt, get_memory_prompt, get_process_prompt, get_action_prompt_OS_world
from mm_agents.PCAgent.chat import init_action_chat, init_reflect_chat, init_memory_chat, add_response

from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from modelscope import snapshot_download, AutoModelForCausalLM, AutoTokenizer, GenerationConfig

from dashscope import MultiModalConversation
import dashscope
import concurrent

from pynput.mouse import Button, Controller
import argparse
import pyautogui
import pyperclip
from mm_agents.PCAgent.merge_strategy import merge_boxes_and_texts, merge_all_icon_boxes, merge_boxes_and_texts_new



import re
import backoff
import dashscope
import google.generativeai as genai
import openai
import requests
import tiktoken
from PIL import Image
from google.api_core.exceptions import InvalidArgument, ResourceExhausted, InternalServerError, BadRequest
from groq import Groq
from requests.exceptions import SSLError

from mm_agents.accessibility_tree_wrap.heuristic_retrieve import filter_nodes, draw_bounding_boxes
from mm_agents.prompts import SYS_PROMPT_IN_SCREENSHOT_OUT_CODE, SYS_PROMPT_IN_SCREENSHOT_OUT_ACTION, \
    SYS_PROMPT_IN_A11Y_OUT_CODE, SYS_PROMPT_IN_A11Y_OUT_ACTION, \
    SYS_PROMPT_IN_BOTH_OUT_CODE, SYS_PROMPT_IN_BOTH_OUT_ACTION, \
    SYS_PROMPT_IN_SOM_OUT_TAG

logger = logging.getLogger("desktopenv.agent")

pure_text_settings = ['a11y_tree']

attributes_ns_ubuntu = "https://accessibility.windows.example.org/ns/attributes"
attributes_ns_windows = "https://accessibility.windows.example.org/ns/attributes"
state_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/state"
state_ns_windows = "https://accessibility.windows.example.org/ns/state"
component_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/component"
component_ns_windows = "https://accessibility.windows.example.org/ns/component"
value_ns_ubuntu = "https://accessibility.ubuntu.example.org/ns/value"
value_ns_windows = "https://accessibility.windows.example.org/ns/value"
class_ns_windows = "https://accessibility.windows.example.org/ns/class"
# More namespaces defined in RAGE, please check desktop_env/server/main.py


import random
from PIL import ImageFont
def cmyk_to_rgb(c, m, y, k):
    r = 255 * (1.0 - c / 255) * (1.0 - k / 255)
    g = 255 * (1.0 - m / 255) * (1.0 - k / 255)
    b = 255 * (1.0 - y / 255) * (1.0 - k / 255)
    return int(r), int(g), int(b)
def draw_coordinates_boxes_on_image(image_path, coordinates, output_image_path, font_path):
    image =Image.open(image_path)
    width, height = image.size
    draw = ImageDraw.Draw(image)
    total_boxes = len(coordinates)
    colors = [(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) for _ in
              range(total_boxes)]
    # padding = height * 0.005

    for i, coord in enumerate(coordinates):
        # color = generate_color_from_hsv_pil(i, total_boxes)
        c, m, y, k = colors[i]
        color = cmyk_to_rgb(c, m, y, k)
        # print(color)

        # coord[0] = coord[0] - padding
        # coord[1] = coord[1] - padding
        # coord[2] = coord[2] + padding
        # coord[3] = coord[3] + padding

        draw.rectangle(coord, outline=color, width=int(height * 0.0025))

        font = ImageFont.truetype(font_path, int(height * 0.012))
        text_x = coord[0] + int(height * 0.0025)
        text_y = max(0, coord[1] - int(height * 0.013))
        draw.text((text_x, text_y), str(i + 1), fill=color, font=font)
    # image.show()
    image = image.convert('RGB')
    image.save(output_image_path)

def split_image_into_4(input_image, output_image_prefix):
    img =Image.open(input_image)
    width, height = img.size

    sub_width = width // 2
    sub_height = height // 2

    # crop into 4 sub images
    quadrants = [
        (0, 0, sub_width, sub_height),
        (sub_width, 0, width, sub_height),
        (0, sub_height, sub_width, height),
        (sub_width, sub_height, width, height)
    ]

    for i, box in enumerate(quadrants):
        sub_img = img.crop(box)
        sub_img.save(f"{output_image_prefix}_part_{i+1}.png")



# Function to encode the image
def encode_image(image_content):
    return base64.b64encode(image_content).decode('utf-8')


def encoded_img_to_pil_img(data_str):
    base64_str = data_str.replace("data:image/png;base64,", "")
    image_data = base64.b64decode(base64_str)
    image = Image.open(BytesIO(image_data))

    return image


def save_to_tmp_img_file(data_str):
    base64_str = data_str.replace("data:image/png;base64,", "")
    image_data = base64.b64decode(base64_str)
    image = Image.open(BytesIO(image_data))

    tmp_img_path = os.path.join(tempfile.mkdtemp(), "tmp_img.png")
    image.save(tmp_img_path)

    return tmp_img_path


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
            "{:}\t{:}\t{:}\t{:}\t{:}\t{:}\t{:}".format(
                node.tag, node.get("name", ""),
                text,
                node.get("{{{:}}}class".format(_attributes_ns), "") if platform == "ubuntu" else node.get("{{{:}}}class".format(class_ns_windows), ""),
                node.get("{{{:}}}description".format(_attributes_ns), ""),
                node.get('{{{:}}}screencoord'.format(_component_ns), ""),
                node.get('{{{:}}}size'.format(_component_ns), "")
            )
        )

    return "\n".join(linearized_accessibility_tree)


def tag_screenshot(screenshot, accessibility_tree, platform="ubuntu"):
    nodes = filter_nodes(ET.fromstring(accessibility_tree), platform=platform, check_image=True)
    # Make tag screenshot
    marks, drew_nodes, element_list, tagged_screenshot = draw_bounding_boxes(nodes, screenshot)

    return marks, drew_nodes, tagged_screenshot, element_list


def parse_actions_from_string(input_string):
    if input_string.strip() in ['WAIT', 'DONE', 'FAIL']:
        return [input_string.strip()]
    # Search for a JSON string within the input string
    actions = []
    matches = re.findall(r'```json\s+(.*?)\s+```', input_string, re.DOTALL)
    if matches:
        # Assuming there's only one match, parse the JSON string into a dictionary
        try:
            for match in matches:
                action_dict = json.loads(match)
                actions.append(action_dict)
            return actions
        except json.JSONDecodeError as e:
            return f"Failed to parse JSON: {e}"
    else:
        matches = re.findall(r'```\s+(.*?)\s+```', input_string, re.DOTALL)
        if matches:
            # Assuming there's only one match, parse the JSON string into a dictionary
            try:
                for match in matches:
                    action_dict = json.loads(match)
                    actions.append(action_dict)
                return actions
            except json.JSONDecodeError as e:
                return f"Failed to parse JSON: {e}"
        else:
            try:
                action_dict = json.loads(input_string)
                return [action_dict]
            except json.JSONDecodeError:
                raise ValueError("Invalid response format: " + input_string)


def parse_code_from_string(input_string):
    input_string = "\n".join([line.strip() for line in input_string.split(';') if line.strip()])
    if input_string.strip() in ['WAIT', 'DONE', 'FAIL']:
        return [input_string.strip()]

    # This regular expression will match both ```code``` and ```python code```
    # and capture the `code` part. It uses a non-greedy match for the content inside.
    pattern = r"```(?:\w+\s+)?(.*?)```"
    # Find all non-overlapping matches in the string
    matches = re.findall(pattern, input_string, re.DOTALL)

    # The regex above captures the content inside the triple backticks.
    # The `re.DOTALL` flag allows the dot `.` to match newline characters as well,
    # so the code inside backticks can span multiple lines.

    # matches now contains all the captured code snippets

    codes = []

    for match in matches:
        match = match.strip()
        commands = ['WAIT', 'DONE', 'FAIL']  # fixme: updates this part when we have more commands

        if match in commands:
            codes.append(match.strip())
        elif match.split('\n')[-1] in commands:
            if len(match.split('\n')) > 1:
                codes.append("\n".join(match.split('\n')[:-1]))
            codes.append(match.split('\n')[-1])
        else:
            codes.append(match)
    print('CODES')
    print(codes)
    print('CODES')
    return codes


def parse_code_from_som_string(input_string, masks):
    # parse the output string by masks
    tag_vars = ""
    for i, mask in enumerate(masks):
        x, y, w, h = mask
        tag_vars += "tag_" + str(i + 1) + "=" + "({}, {})".format(int(x + w // 2), int(y + h // 2))
        tag_vars += "\n"

    actions = parse_code_from_string(input_string)

    for i, action in enumerate(actions):
        if action.strip() in ['WAIT', 'DONE', 'FAIL']:
            pass
        else:
            action = tag_vars + action
            actions[i] = action

    return actions
def get_all_files_in_folder(folder_path):
    file_list = []
    for file_name in os.listdir(folder_path):
        file_list.append(file_name)
    return file_list

def trim_accessibility_tree(linearized_accessibility_tree, max_tokens):
    enc = tiktoken.encoding_for_model("gpt-4")
    tokens = enc.encode(linearized_accessibility_tree)
    if len(tokens) > max_tokens:
        linearized_accessibility_tree = enc.decode(tokens[:max_tokens])
        linearized_accessibility_tree += "[...]\n"
    return linearized_accessibility_tree


class PromptAgent:
    def __init__(
            self,
            platform="ubuntu",
            model="gpt-4-vision-preview",
            max_tokens=1500,
            top_p=0.9,
            temperature=0.5,
            action_space="computer_13",
            observation_type="screenshot_a11y_tree",
            # observation_type can be in ["screenshot", "a11y_tree", "screenshot_a11y_tree", "som"]
            max_trajectory_length=3,
            a11y_tree_max_tokens=10000
    ):
        self.platform = platform
        self.model = model
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.temperature = temperature
        self.action_space = action_space
        self.observation_type = observation_type
        self.max_trajectory_length = max_trajectory_length
        self.a11y_tree_max_tokens = a11y_tree_max_tokens

        self.thoughts = []
        self.actions = []
        self.observations = []

        if observation_type == "screenshot":
            if action_space == "computer_13":
                self.system_message = SYS_PROMPT_IN_SCREENSHOT_OUT_ACTION
            elif action_space == "pyautogui":
                self.system_message = SYS_PROMPT_IN_SCREENSHOT_OUT_CODE
            else:
                raise ValueError("Invalid action space: " + action_space)
        elif observation_type == "a11y_tree":
            if action_space == "computer_13":
                self.system_message = SYS_PROMPT_IN_A11Y_OUT_ACTION
            elif action_space == "pyautogui":
                self.system_message = SYS_PROMPT_IN_A11Y_OUT_CODE
            else:
                raise ValueError("Invalid action space: " + action_space)
        elif observation_type == "screenshot_a11y_tree":
            if action_space == "computer_13":
                self.system_message = SYS_PROMPT_IN_BOTH_OUT_ACTION
            elif action_space == "pyautogui":
                self.system_message = SYS_PROMPT_IN_BOTH_OUT_CODE
            else:
                raise ValueError("Invalid action space: " + action_space)
        elif observation_type == "som":
            if action_space == "computer_13":
                raise ValueError("Invalid action space: " + action_space)
            elif action_space == "pyautogui":
                self.system_message = SYS_PROMPT_IN_SOM_OUT_TAG
            else:
                raise ValueError("Invalid action space: " + action_space)
        else:
            raise ValueError("Invalid experiment type: " + observation_type)

        self.groundingdino_dir = 'C:\\Users\mr\.cache\modelscope\hub\AI-ModelScope\GroundingDINO'
        #snapshot_download('AI-ModelScope/GroundingDINO', revision='v1.0.0')
        self.groundingdino_model = pipeline('grounding-dino-task', model=self.groundingdino_dir)
        self.ocr_detection = pipeline(Tasks.ocr_detection, model='C:\\Users\mr\.cache\modelscope\hub\damo/cv_resnet18_ocr-detection-line-level_damo')
        self.ocr_recognition = pipeline(Tasks.ocr_recognition, model='C:\\Users\mr\.cache\modelscope\hub\damo/cv_convnextTiny_ocr-recognition-document_damo')

        # Downloading: 100 % |██████████ | 29.6
        # k / 29.6
        # k[00:00 < 00:00, 58.9
        # kB / s]2025 - 03 - 23
        # 13: 13:29, 794 - modelscope - INFO - initiate
        # model
        # from C:\Users\mr\.cache\modelscope\hub\damo\cv_convnextTiny_ocr - recognition - document_damo
        # 2025 - 03 - 23
        # 13: 13:29, 795 - modelscope - INFO - initiate
        # model
        # from location C:\Users\mr\.cache\modelscope\hub\damo\cv_convnextTiny_ocr - recognition - document_damo.
        # 2025 - 03 - 23
        # 13: 13:29, 797 - modelscope - INFO - initialize
        # model
        # from C:\Users\mr\.cache\modelscope\hub\damo\cv_convnextTiny_ocr - recognition - document_damo
        # 2025 - 03 - 23
        # 13: 13:29, 976 - modelscope - INFO - cuda is not available, using
        # cpu
        # instead.
        # 2025 - 03 - 23
        # 13: 13:29, 976 - modelscope - INFO - loading
        # model
        # from dir C:\Users\mr\.cache\modelscope\hub\damo\cv_convnextTiny_ocr - recognition - document_damo
        # from modelscope import pipeline, snapshot_download, Tasks
        #
        # # Automatically download the GroundingDINO model
        # self.groundingdino_dir = snapshot_download('AI-ModelScope/GroundingDINO', revision='v1.0.0')
        # self.groundingdino_model = pipeline('grounding-dino-task', model=self.groundingdino_dir)
        #
        # # Automatically download the OCR detection model
        # self.ocr_detection_model = snapshot_download('damo/cv_resnet18_ocr-detection-line-level_damo')
        # self.ocr_detection = pipeline(Tasks.ocr_detection, model=self.ocr_detection_model)

        # Automatically download the OCR recognition model
        # self.ocr_recognition_model = snapshot_download('damo/cv_convnextTiny_ocr-recognition-document_damo')
        # self.ocr_recognition = pipeline(Tasks.ocr_recognition, model=self.ocr_recognition_model)
        self.thought_history = []
        self.summary_history = []
        self.action_history = []
        self.completed_requirements = ""
        self.error_flag = False
        self.reflection_thought = ""
        self.summary = ""
        self.action = ""
        self.font_path = "Times Regular.ttf"
        self.temp_file = "temp"

        if os.path.exists(self.temp_file):
            shutil.rmtree(self.temp_file)
        os.mkdir(self.temp_file)
    def reset(self):
        self.thought_history = []
        self.summary_history = []
        self.action_history = []
        self.completed_requirements = ""
        self.error_flag = False
        self.reflection_thought = ""
        self.summary = ""
        self.action = ""

    def get_perception_infos(self, screenshot_file, screenshot_som_file, font_path):
        image = Image.open(screenshot_file)
        total_width, total_height =image.size

        # Partition Image into 4 parts
        split_image_into_4(screenshot_file, './screenshot/screenshot')
        img_list = ['./screenshot/screenshot_part_1.png', './screenshot/screenshot_part_2.png',
                    './screenshot/screenshot_part_3.png', './screenshot/screenshot_part_4.png']
        img_x_list = [0, total_width / 2, 0, total_width / 2]
        img_y_list = [0, 0, total_height / 2, total_height / 2]
        coordinates = []
        texts = []
        padding = total_height * 0.0025  # 10

        for i, img in enumerate(img_list):
            width, height = Image.open(img).size

            sub_text, sub_coordinates = ocr(img, self.ocr_detection, self.ocr_recognition)
            for coordinate in sub_coordinates:
                coordinate[0] = int(max(0, img_x_list[i] + coordinate[0] - padding))
                coordinate[2] = int(min(total_width, img_x_list[i] + coordinate[2] + padding))
                coordinate[1] = int(max(0, img_y_list[i] + coordinate[1] - padding))
                coordinate[3] = int(min(total_height, img_y_list[i] + coordinate[3] + padding))

            sub_text_merge, sub_coordinates_merge = merge_boxes_and_texts_new(sub_text, sub_coordinates)
            coordinates.extend(sub_coordinates_merge)
            texts.extend(sub_text_merge)
        merged_text, merged_text_coordinates = merge_boxes_and_texts(texts, coordinates)

        coordinates = []
        for i, img in enumerate(img_list):
            width, height = Image.open(img).size
            sub_coordinates = det(img, "icon", self.groundingdino_model)
            for coordinate in sub_coordinates:
                coordinate[0] = int(max(0, img_x_list[i] + coordinate[0] - padding))
                coordinate[2] = int(min(total_width, img_x_list[i] + coordinate[2] + padding))
                coordinate[1] = int(max(0, img_y_list[i] + coordinate[1] - padding))
                coordinate[3] = int(min(total_height, img_y_list[i] + coordinate[3] + padding))

            sub_coordinates = merge_all_icon_boxes(sub_coordinates)
            coordinates.extend(sub_coordinates)
        merged_icon_coordinates = merge_all_icon_boxes(coordinates)

        if 1:
            rec_list = merged_text_coordinates + merged_icon_coordinates
            draw_coordinates_boxes_on_image(screenshot_file, copy.deepcopy(rec_list), screenshot_som_file, font_path)
        else:
            draw_coordinates_boxes_on_image(screenshot_file, copy.deepcopy(merged_icon_coordinates),
                                            screenshot_som_file,
                                            font_path)

        mark_number = 0
        perception_infos = []

        for i in range(len(merged_text_coordinates)):
            if 1:
                mark_number += 1
                perception_info = {"text": "mark number: " + str(mark_number) + " text: " + merged_text[i],
                                   "coordinates": merged_text_coordinates[i]}
            else:
                perception_info = {"text": "text: " + merged_text[i], "coordinates": merged_text_coordinates[i]}
            perception_infos.append(perception_info)

        for i in range(len(merged_icon_coordinates)):
            if 1:
                mark_number += 1
                perception_info = {"text": "mark number: " + str(mark_number) + " icon",
                                   "coordinates": merged_icon_coordinates[i]}
            else:
                perception_info = {"text": "icon", "coordinates": merged_icon_coordinates[i]}
            perception_infos.append(perception_info)
            image_box = []

            for i in range(len(image_box)):
                crop(screenshot_file, image_box[i], image_id[i])

            images = get_all_files_in_folder(self.temp_file)
            if len(images) > 0:
                images = sorted(images, key=lambda x: int(x.split('/')[-1].split('.')[0]))
                image_id = [int(image.split('/')[-1].split('.')[0]) for image in images]
                icon_map = {}
                prompt = 'This image is an icon from a computer screen. Please briefly describe the shape and color of this icon in one sentence.'
                if caption_call_method == "local":
                    for i in range(len(images)):
                        image_path = os.path.join(self.temp_file, images[i])
                        icon_width, icon_height = Image.open(image_path).size
                        if icon_height > 0.8 * height or icon_width * icon_height > 0.2 * width * height:
                            des = "None"
                        else:
                            des = generate_local(tokenizer, model, image_path, prompt)
                        icon_map[i + 1] = des
                else:
                    for i in range(len(images)):
                        images[i] = os.path.join(temp_file, images[i])
                    icon_map = generate_api(images, prompt)
                for i, j in zip(image_id, range(1, len(image_id) + 1)):
                    if icon_map.get(j):
                        perception_infos[i]['text'] += ": " + icon_map[j]


        for i in range(len(perception_infos)):
            perception_infos[i]['coordinates'] = [
                int((perception_infos[i]['coordinates'][0] + perception_infos[i]['coordinates'][2]) / 2),
                int((perception_infos[i]['coordinates'][1] + perception_infos[i]['coordinates'][3]) / 2)]
        # elif args.location_info == 'icon_center':
        #     for i in range(len(perception_infos)):
        #         if 'icon' in perception_infos[i]['text']:
        #             perception_infos[i]['coordinates'] = [
        #                 int((perception_infos[i]['coordinates'][0] + perception_infos[i]['coordinates'][2]) / 2),
        #                 int((perception_infos[i]['coordinates'][1] + perception_infos[i]['coordinates'][3]) / 2)]

        return perception_infos, total_width, total_height

    def predict(self, instruction: str, obs: Dict) -> List:
        """
        Predict the next action(s) based on the current observation.
        """
        screenshot_file = "./screenshot/screenshot.png"

        screenshot_som_file = "./screenshot/screenshot_som.png"
        with open(screenshot_file, 'wb') as file:
            file.write(obs["screenshot"])
        perception_infos, width, height = self.get_perception_infos(screenshot_file, screenshot_som_file, font_path=self.font_path)
        os.makedirs(os.path.dirname(screenshot_file), exist_ok=True)

        print('SAVE screenshot_file')
        system_message = self.system_message + "\nYou are asked to complete the following task: {}".format(instruction)
        prompt_action = get_action_prompt_OS_world(instruction, perception_infos, width, height, self.thought_history,
                                          self.summary_history, self.action_history, self.summary, self.action, self.reflection_thought,
                                          "", self.error_flag, self.completed_requirements, "", 1,
                                          0, 'center')

        chat_action = init_action_chat()
        chat_action[0][1][0].update({"text": system_message})
        print(chat_action)
        if 1:
            chat_action = add_response("user", prompt_action, chat_action, [screenshot_file, screenshot_som_file])

        output_action = inference_chat(chat_action, 'gpt-4o', "https://api.openai.com/v1/chat/completions", os.environ['OPENAI_API_KEY'])
        # output_action = self.call_llm({
        #     "model": self.model,
        #     "messages": chat_action,
        #     "max_tokens": self.max_tokens,
        #     "top_p": self.top_p,
        #     "temperature": self.temperature
        # })
        print('output_action')
        thought = output_action.split("### Thought ###")[-1].split("### Action ###")[0]
        summary = output_action.split("### Operation ###")[-1].replace("\n", " ").replace("  ", " ").strip()
        action = output_action.split("### Action ###")[-1].split("### Operation ###")[0].strip()
        chat_action = add_response("assistant", output_action, chat_action)
        status = "#" * 50 + " Decision " + "#" * 50
        print(status)
        print(output_action)
        print('#' * len(status))

        time.sleep(2)  # wait for the action to be excuted


        last_screenshot_file = "./screenshot/last_screenshot.png"
        last_screenshot_som_file = "./screenshot/last_screenshot_som.png"
        if os.path.exists(last_screenshot_file):
            perception_infos, width, height = self.get_perception_infos(screenshot_file, screenshot_som_file,
                                                                        font_path=self.font_path)
            last_perception_infos = copy.deepcopy(perception_infos)
            # os.remove(last_screenshot_file)

            # if 1:
            #
            #     # if os.path.exists(last_screenshot_som_file):
            #     #     os.remove(last_screenshot_som_file)
            #     # os.rename(screenshot_som_file, last_screenshot_som_file)



            prompt_reflect = get_reflect_prompt(instruction, last_perception_infos, perception_infos, width, height,
                                                summary, action, "")
            chat_reflect = init_reflect_chat()
            chat_reflect = add_response("user", prompt_reflect, chat_reflect, [last_screenshot_file, screenshot_file])

            output_reflect = inference_chat(chat_reflect, 'gpt-4o', "https://api.openai.com/v1/chat/completions", os.environ['OPENAI_API_KEY'])
            reflection_thought = output_reflect.split("### Thought ###")[-1].split("### Answer ###")[0].replace("\n",
                                                                                                                " ").strip()
            reflect = output_reflect.split("### Answer ###")[-1].replace("\n", " ").strip()
            chat_reflect = add_response("assistant", output_reflect, chat_reflect)
            status = "#" * 50 + " Reflection " + "#" * 50
            print(status)
            print(output_reflect)
            print('#' * len(status))

            if 'A' in reflect:
                self.thought_history.append(thought)
                self.summary_history.append(summary)
                self.action_history.append(action)

                prompt_planning = get_process_prompt(instruction, self.thought_history, self.summary_history, self.action_history,
                                                     self.completed_requirements, "")
                chat_planning = init_memory_chat()
                chat_planning = add_response("user", prompt_planning, chat_planning)
                output_planning = inference_chat(chat_planning, 'gpt-4o', "https://api.openai.com/v1/chat/completions", os.environ['OPENAI_API_KEY'])
                chat_planning = add_response("assistant", output_planning, chat_planning)
                status = "#" * 50 + " Planning " + "#" * 50
                print(status)
                print(output_planning)
                print('#' * len(status))
                self.completed_requirements = output_planning.split("### Completed contents ###")[-1].replace("\n",
                                                                                                         " ").strip()

                self.error_flag = False

            elif 'B' in reflect:
                self.error_flag = True
                # presskey('esc')

            elif 'C' in reflect:
                self.error_flag = True
                # presskey('esc')

        else:
            self.thought_history.append(thought)
            self.summary_history.append(summary)
            self.action_history.append(action)

            prompt_planning = get_process_prompt(instruction, self.thought_history, self.summary_history, self.action_history,
                                                 self.completed_requirements, "")
            chat_planning = init_memory_chat()
            chat_planning = add_response("user", prompt_planning, chat_planning)
            output_planning = inference_chat(chat_planning, 'gpt-4o', "https://api.openai.com/v1/chat/completions", os.environ['OPENAI_API_KEY'])
            chat_planning = add_response("assistant", output_planning, chat_planning)
            status = "#" * 50 + " Planning " + "#" * 50
            print(status)
            print(output_planning)
            print('#' * len(status))
            self.completed_requirements = output_planning.split("### Completed contents ###")[-1].replace("\n", " ").strip()

        # os.remove(last_screenshot_file)
        # # if args.use_som == 1:
        # os.remove(last_screenshot_som_file)
        if os.path.exists(last_screenshot_som_file):
            os.remove(last_screenshot_som_file)
        if os.path.exists(last_screenshot_file):
            os.remove(last_screenshot_file)
        os.rename(screenshot_file, last_screenshot_file)
        os.rename(screenshot_som_file, last_screenshot_som_file)
        # Append trajectory

        # with open("messages.json", "w") as f:
        #     f.write(json.dumps(messages, indent=4))

        # logger.info("PROMPT: %s", messages)


        logger.info("RESPONSE: %s", action)

        try:
            actions = self.parse_actions(action, None)
        except ValueError as e:
            print("Failed to parse action from response", e)
            actions = None

        return output_action, actions

    @backoff.on_exception(
        backoff.constant,
        # here you should add more model exceptions as you want,
        # but you are forbidden to add "Exception", that is, a common type of exception
        # because we want to catch this kind of Exception in the outside to ensure each example won't exceed the time limit
        (
                # General exceptions
                SSLError,

                # OpenAI exceptions
                openai.RateLimitError,
                openai.BadRequestError,
                openai.InternalServerError,

                # Google exceptions
                InvalidArgument,
                ResourceExhausted,
                InternalServerError,
                BadRequest,

                # Groq exceptions
                # todo: check
        ),
        interval=30,
        max_tries=10
    )
    def call_llm(self, payload):

        if self.model.startswith("gpt"):
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"
            }
            logger.info("Generating content with GPT model: %s", self.model)
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                verify=False
            )

            if response.status_code != 200:
                if response.json()['error']['code'] == "context_length_exceeded":
                    logger.error("Context length exceeded. Retrying with a smaller context.")
                    payload["messages"] = [payload["messages"][0]] + payload["messages"][-1:]
                    retry_response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    if retry_response.status_code != 200:
                        logger.error(
                            "Failed to call LLM even after attempt on shortening the history: " + retry_response.text)
                        return ""

                logger.error("Failed to call LLM: " + response.text)
                time.sleep(5)
                return ""
            else:
                return response.json()['choices'][0]['message']['content']

        elif self.model.startswith("claude"):
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            claude_messages = []

            for i, message in enumerate(messages):
                claude_message = {
                    "role": message["role"],
                    "content": []
                }
                assert len(message["content"]) in [1, 2], "One text, or one text with one image"
                for part in message["content"]:

                    if part['type'] == "image_url":
                        image_source = {}
                        image_source["type"] = "base64"
                        image_source["media_type"] = "image/png"
                        image_source["data"] = part['image_url']['url'].replace("data:image/png;base64,", "")
                        claude_message['content'].append({"type": "image", "source": image_source})

                    if part['type'] == "text":
                        claude_message['content'].append({"type": "text", "text": part['text']})

                claude_messages.append(claude_message)

            # the claude not support system message in our endpoint, so we concatenate it at the first user message
            if claude_messages[0]['role'] == "system":
                claude_system_message_item = claude_messages[0]['content'][0]
                claude_messages[1]['content'].insert(0, claude_system_message_item)
                claude_messages.pop(0)

            logger.debug("CLAUDE MESSAGE: %s", repr(claude_messages))

            headers = {
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": claude_messages,
                "temperature": temperature,
                "top_p": top_p
            }

            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            )

            if response.status_code != 200:

                logger.error("Failed to call LLM: " + response.text)
                time.sleep(5)
                return ""
            else:
                return response.json()['content'][0]['text']

        elif self.model.startswith("mistral"):
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            assert self.observation_type in pure_text_settings, f"The model {self.model} can only support text-based input, please consider change based model or settings"

            mistral_messages = []

            for i, message in enumerate(messages):
                mistral_message = {
                    "role": message["role"],
                    "content": ""
                }

                for part in message["content"]:
                    mistral_message['content'] = part['text'] if part['type'] == "text" else ""

                mistral_messages.append(mistral_message)

            from openai import OpenAI

            client = OpenAI(api_key=os.environ["TOGETHER_API_KEY"],
                            base_url='https://api.together.xyz',
                            )

            flag = 0
            while True:
                try:
                    if flag > 20:
                        break
                    logger.info("Generating content with model: %s", self.model)
                    response = client.chat.completions.create(
                        messages=mistral_messages,
                        model=self.model,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        temperature=temperature
                    )
                    break
                except:
                    if flag == 0:
                        mistral_messages = [mistral_messages[0]] + mistral_messages[-1:]
                    else:
                        mistral_messages[-1]["content"] = ' '.join(mistral_messages[-1]["content"].split()[:-500])
                    flag = flag + 1

            try:
                return response.choices[0].message.content
            except Exception as e:
                print("Failed to call LLM: " + str(e))
                return ""

        elif self.model.startswith("THUDM"):
            # THUDM/cogagent-chat-hf
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            cog_messages = []

            for i, message in enumerate(messages):
                cog_message = {
                    "role": message["role"],
                    "content": []
                }

                for part in message["content"]:
                    if part['type'] == "image_url":
                        cog_message['content'].append(
                            {"type": "image_url", "image_url": {"url": part['image_url']['url']}})

                    if part['type'] == "text":
                        cog_message['content'].append({"type": "text", "text": part['text']})

                cog_messages.append(cog_message)

            # the cogagent not support system message in our endpoint, so we concatenate it at the first user message
            if cog_messages[0]['role'] == "system":
                cog_system_message_item = cog_messages[0]['content'][0]
                cog_messages[1]['content'].insert(0, cog_system_message_item)
                cog_messages.pop(0)

            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "messages": cog_messages,
                "temperature": temperature,
                "top_p": top_p
            }

            base_url = "http://127.0.0.1:8000"

            response = requests.post(f"{base_url}/v1/chat/completions", json=payload, stream=False)
            if response.status_code == 200:
                decoded_line = response.json()
                content = decoded_line.get("choices", [{}])[0].get("message", "").get("content", "")
                return content
            else:
                print("Failed to call LLM: ", response.status_code)
                return ""

        elif self.model in ["gemini-pro", "gemini-pro-vision"]:
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            if self.model == "gemini-pro":
                assert self.observation_type in pure_text_settings, f"The model {self.model} can only support text-based input, please consider change based model or settings"

            gemini_messages = []
            for i, message in enumerate(messages):
                role_mapping = {
                    "assistant": "model",
                    "user": "user",
                    "system": "system"
                }
                gemini_message = {
                    "role": role_mapping[message["role"]],
                    "parts": []
                }
                assert len(message["content"]) in [1, 2], "One text, or one text with one image"

                # The gemini only support the last image as single image input
                if i == len(messages) - 1:
                    for part in message["content"]:
                        gemini_message['parts'].append(part['text']) if part['type'] == "text" \
                            else gemini_message['parts'].append(encoded_img_to_pil_img(part['image_url']['url']))
                else:
                    for part in message["content"]:
                        gemini_message['parts'].append(part['text']) if part['type'] == "text" else None

                gemini_messages.append(gemini_message)

            # the gemini not support system message in our endpoint, so we concatenate it at the first user message
            if gemini_messages[0]['role'] == "system":
                gemini_messages[1]['parts'][0] = gemini_messages[0]['parts'][0] + "\n" + gemini_messages[1]['parts'][0]
                gemini_messages.pop(0)

            # since the gemini-pro-vision donnot support multi-turn message
            if self.model == "gemini-pro-vision":
                message_history_str = ""
                for message in gemini_messages:
                    message_history_str += "<|" + message['role'] + "|>\n" + message['parts'][0] + "\n"
                gemini_messages = [{"role": "user", "parts": [message_history_str, gemini_messages[-1]['parts'][1]]}]
                # gemini_messages[-1]['parts'][1].save("output.png", "PNG")

            # print(gemini_messages)
            api_key = os.environ.get("GENAI_API_KEY")
            assert api_key is not None, "Please set the GENAI_API_KEY environment variable"
            genai.configure(api_key=api_key)
            logger.info("Generating content with Gemini model: %s", self.model)
            request_options = {"timeout": 120}
            gemini_model = genai.GenerativeModel(self.model)

            response = gemini_model.generate_content(
                gemini_messages,
                generation_config={
                    "candidate_count": 1,
                    # "max_output_tokens": max_tokens,
                    "top_p": top_p,
                    "temperature": temperature
                },
                safety_settings={
                    "harassment": "block_none",
                    "hate": "block_none",
                    "sex": "block_none",
                    "danger": "block_none"
                },
                request_options=request_options
            )
            return response.text

        elif self.model == "gemini-1.5-pro-latest":
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            gemini_messages = []
            for i, message in enumerate(messages):
                role_mapping = {
                    "assistant": "model",
                    "user": "user",
                    "system": "system"
                }
                assert len(message["content"]) in [1, 2], "One text, or one text with one image"
                gemini_message = {
                    "role": role_mapping[message["role"]],
                    "parts": []
                }

                # The gemini only support the last image as single image input
                for part in message["content"]:

                    if part['type'] == "image_url":
                        # Put the image at the beginning of the message
                        gemini_message['parts'].insert(0, encoded_img_to_pil_img(part['image_url']['url']))
                    elif part['type'] == "text":
                        gemini_message['parts'].append(part['text'])
                    else:
                        raise ValueError("Invalid content type: " + part['type'])

                gemini_messages.append(gemini_message)

            # the system message of gemini-1.5-pro-latest need to be inputted through model initialization parameter
            system_instruction = None
            if gemini_messages[0]['role'] == "system":
                system_instruction = gemini_messages[0]['parts'][0]
                gemini_messages.pop(0)

            api_key = os.environ.get("GENAI_API_KEY")
            assert api_key is not None, "Please set the GENAI_API_KEY environment variable"
            genai.configure(api_key=api_key)
            logger.info("Generating content with Gemini model: %s", self.model)
            request_options = {"timeout": 120}
            gemini_model = genai.GenerativeModel(
                self.model,
                system_instruction=system_instruction
            )

            with open("response.json", "w") as f:
                messages_to_save = []
                for message in gemini_messages:
                    messages_to_save.append({
                        "role": message["role"],
                        "content": [part if isinstance(part, str) else "image" for part in message["parts"]]
                    })
                json.dump(messages_to_save, f, indent=4)

            response = gemini_model.generate_content(
                gemini_messages,
                generation_config={
                    "candidate_count": 1,
                    # "max_output_tokens": max_tokens,
                    "top_p": top_p,
                    "temperature": temperature
                },
                safety_settings={
                    "harassment": "block_none",
                    "hate": "block_none",
                    "sex": "block_none",
                    "danger": "block_none"
                },
                request_options=request_options
            )

            return response.text

        elif self.model == "llama3-70b":
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            assert self.observation_type in pure_text_settings, f"The model {self.model} can only support text-based input, please consider change based model or settings"

            groq_messages = []

            for i, message in enumerate(messages):
                groq_message = {
                    "role": message["role"],
                    "content": ""
                }

                for part in message["content"]:
                    groq_message['content'] = part['text'] if part['type'] == "text" else ""

                groq_messages.append(groq_message)

            # The implementation based on Groq API
            client = Groq(
                api_key=os.environ.get("GROQ_API_KEY"),
            )

            flag = 0
            while True:
                try:
                    if flag > 20:
                        break
                    logger.info("Generating content with model: %s", self.model)
                    response = client.chat.completions.create(
                        messages=groq_messages,
                        model="llama3-70b-8192",
                        max_tokens=max_tokens,
                        top_p=top_p,
                        temperature=temperature
                    )
                    break
                except:
                    if flag == 0:
                        groq_messages = [groq_messages[0]] + groq_messages[-1:]
                    else:
                        groq_messages[-1]["content"] = ' '.join(groq_messages[-1]["content"].split()[:-500])
                    flag = flag + 1

            try:
                return response.choices[0].message.content
            except Exception as e:
                print("Failed to call LLM: " + str(e))
                return ""

        elif self.model.startswith("qwen"):
            messages = payload["messages"]
            max_tokens = payload["max_tokens"]
            top_p = payload["top_p"]
            temperature = payload["temperature"]

            qwen_messages = []

            for i, message in enumerate(messages):
                qwen_message = {
                    "role": message["role"],
                    "content": []
                }
                assert len(message["content"]) in [1, 2], "One text, or one text with one image"
                for part in message["content"]:
                    qwen_message['content'].append(
                        {"image": "file://" + save_to_tmp_img_file(part['image_url']['url'])}) if part[
                                                                                                      'type'] == "image_url" else None
                    qwen_message['content'].append({"text": part['text']}) if part['type'] == "text" else None

                qwen_messages.append(qwen_message)

            flag = 0
            while True:
                try:
                    if flag > 20:
                        break
                    logger.info("Generating content with model: %s", self.model)

                    if self.model in ["qwen-vl-plus", "qwen-vl-max"]:
                        response = dashscope.MultiModalConversation.call(
                            model=self.model,
                            messages=qwen_messages,
                            result_format="message",
                            max_length=max_tokens,
                            top_p=top_p,
                            temperature=temperature
                        )

                    elif self.model in ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-0428", "qwen-max-0403",
                                        "qwen-max-0107", "qwen-max-longcontext"]:
                        response = dashscope.Generation.call(
                            model=self.model,
                            messages=qwen_messages,
                            result_format="message",
                            max_length=max_tokens,
                            top_p=top_p,
                            temperature=temperature
                        )

                    else:
                        raise ValueError("Invalid model: " + self.model)

                    if response.status_code == HTTPStatus.OK:
                        break
                    else:
                        logger.error('Request id: %s, Status code: %s, error code: %s, error message: %s' % (
                            response.request_id, response.status_code,
                            response.code, response.message
                        ))
                        raise Exception("Failed to call LLM: " + response.message)
                except:
                    if flag == 0:
                        qwen_messages = [qwen_messages[0]] + qwen_messages[-1:]
                    else:
                        for i in range(len(qwen_messages[-1]["content"])):
                            if "text" in qwen_messages[-1]["content"][i]:
                                qwen_messages[-1]["content"][i]["text"] = ' '.join(
                                    qwen_messages[-1]["content"][i]["text"].split()[:-500])
                    flag = flag + 1

            try:
                if self.model in ["qwen-vl-plus", "qwen-vl-max"]:
                    return response['output']['choices'][0]['message']['content'][0]['text']
                else:
                    return response['output']['choices'][0]['message']['content']

            except Exception as e:
                print("Failed to call LLM: " + str(e))
                return ""

        else:
            raise ValueError("Invalid model: " + self.model)

    def parse_actions(self, response: str, masks=None):

        if self.observation_type in ["screenshot", "a11y_tree", "screenshot_a11y_tree"]:
            # parse from the response
            if self.action_space == "computer_13":
                actions = parse_actions_from_string(response)
            elif self.action_space == "pyautogui":
                actions = parse_code_from_string(response)
            else:
                raise ValueError("Invalid action space: " + self.action_space)

            self.actions.append(actions)

            return actions
        elif self.observation_type in ["som"]:
            # parse from the response
            if self.action_space == "computer_13":
                raise ValueError("Invalid action space: " + self.action_space)
            elif self.action_space == "pyautogui":
                actions = parse_code_from_som_string(response, masks)
            else:
                raise ValueError("Invalid action space: " + self.action_space)

            self.actions.append(actions)

            return actions

    def reset(self, _logger=None):
        global logger
        logger = _logger if _logger is not None else logging.getLogger("desktopenv.agent")

        self.thoughts = []
        self.actions = []
        self.observations = []
