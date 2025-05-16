import datetime
import json
import logging
import os
import base64
import time
from io import BytesIO
import shutil
from PIL import Image, ImageDraw, ImageFont


def encode_image(image_content):

    return base64.b64encode(image_content).decode('utf-8')


def decode_image(base64_string):

    image_data = base64.b64decode(base64_string)
    return Image.open(BytesIO(image_data))


from PIL import Image, ImageDraw, ImageFont

def add_popup_to_image(image, text="Hello!"):
    """Embeds a bold and large text in the center of the image, automatically adjusting font size to fit."""
    draw = ImageDraw.Draw(image)
    img_width, img_height = image.size

    # Set an initial maximum font size
    max_font_size = img_height // 8  # Increase the initial max font size
    try:
        font = ImageFont.truetype("arialbd.ttf", max_font_size)  # Use bold font
    except IOError:
        try:
            font = ImageFont.truetype("arial.ttf", max_font_size)  # Fallback font
        except IOError:
            font = ImageFont.load_default()

    # Adjust font size to fit within the image
    while True:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if text_width <= img_width * 0.8 and text_height <= img_height * 0.2:
            break
        max_font_size -= 1
        if max_font_size <= 10:
            break  # Prevents the font from getting too small
        try:
            font = ImageFont.truetype("arialbd.ttf", max_font_size)
        except IOError:
            font = ImageFont.load_default()

    # Calculate text position (centered)
    text_x = (img_width - text_width) // 2
    text_y = (img_height - text_height) // 2

    # Draw the text multiple times with slight offsets to simulate bold effect
    offsets = [(0, 0), (1, 0), (0, 1), (1, 1)]  # Simulated bold effect
    for dx, dy in offsets:
        draw.text((text_x + dx, text_y + dy), text, fill="black", font=font)

    return image


def process_image_with_popup(obs, popup_text="Custom Text"):

    logger.info("Popup Screenshot")
    base64_image = encode_image(obs["screenshot"])
    image = decode_image(base64_image)


    # image.show(title="Original Image")

    image_with_popup = add_popup_to_image(image, popup_text)


    # image_with_popup.show(title="Image with Popup")

    buffered = BytesIO()
    image_with_popup.save(buffered, format="PNG")
    buffered.seek(0)

    # 替换 obs["screenshot"]
    obs["screenshot"] = buffered.getvalue()
    return obs



from wrapt_timeout_decorator import *

logger = logging.getLogger("desktopenv.experiment")


def run_single_example(agent, env, example, max_steps, instruction, args, example_result_dir, scores, popup):
    runtime_logger = setup_logger(example, example_result_dir)
    agent.reset(runtime_logger)
    obs = env.reset(task_config=example)

    if popup == "true":
        obs = process_image_with_popup(obs, example["popup_text"])
    done = False
    step_idx = 0
    env.controller.start_recording()
    while not done and step_idx < max_steps:
        response, actions = agent.predict(
            instruction,
            obs
        )
        for action in actions:
            # Capture the timestamp before executing the action
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Step %d: %s", step_idx + 1, action)
            obs, reward, done, info = env.step(action, args.sleep_after_execution)
            if popup == "true":
                obs = process_image_with_popup(obs, example["popup_text"])
            logger.info("Reward: %.2f", reward)
            logger.info("Done: %s", done)
            # Save screenshot and trajectory information
            with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
                      "wb") as _f:
                _f.write(obs['screenshot'])
            with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action_timestamp": action_timestamp,
                    "action": action,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
                }))
                f.write("\n")
            if done:
                agent.reset()
                logger.info("The episode is done.")
                break
        step_idx += 1
    # result = env.evaluate()
    #  [0,1]
    # logger.info("Result: %.2f", result)
    # scores.append(result)
    # with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
    #     f.write(f"{result}\n")
    env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))

def eval_single_example_safety(agent, env, example, max_steps, instruction, args, example_result_dir, scores, popup):
    runtime_logger = setup_logger(example, example_result_dir)
    agent.reset(runtime_logger)
    example["config"].insert(0, {
        "type": "execute",
        "parameters": {
            "command": "xdotool search --onlyvisible . windowkill %@",
            "shell": True
        }
    })

    obs = env.reset(task_config=example)

    if popup == "true":
        obs = process_image_with_popup(obs, example["popup_text"])
    done = False
    step_idx = 0
    # env.controller.start_recording()
    # while not done and step_idx < max_steps:
    #     response, actions = agent.predict(
    #         instruction,
    #         obs
    #     )
    #     for action in actions:
    #         # Capture the timestamp before executing the action
    #         action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
    #         logger.info("Step %d: %s", step_idx + 1, action)
    #         obs, reward, done, info = env.step(action, args.sleep_after_execution)
    #         if popup == "true":
    #             obs = process_image_with_popup(obs, example["popup_text"])
    #         logger.info("Reward: %.2f", reward)
    #         logger.info("Done: %s", done)
    #         # Save screenshot and trajectory information
    #         with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
    #                   "wb") as _f:
    #             _f.write(obs['screenshot'])
    #         with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
    #             f.write(json.dumps({
    #                 "step_num": step_idx + 1,
    #                 "action_timestamp": action_timestamp,
    #                 "action": action,
    #                 "reward": reward,
    #                 "done": done,
    #                 "info": info,
    #                 "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
    #             }))
    #             f.write("\n")
    #         if done:
    #             agent.reset()
    #             logger.info("The episode is done.")
    #             break
    #     step_idx += 1
    result = env.evaluate()
    logger.info("Result: %s", result)  # 适用于列表
    if isinstance(result, int):
        result = str(result)

    scores.append(result)

    result_str = " ".join(map(str, result))
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(result_str + "\n")
    # env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))


    shutil.rmtree("screenshot", ignore_errors=True)
    os.makedirs("screenshot", exist_ok=True)



def run_single_example_safety_auto(agent, env, example, max_steps, instruction, args, example_result_dir, scores, popup):
    runtime_logger = setup_logger(example, example_result_dir)
    agent.reset(runtime_logger)
    example["config"]=[
        {
            "type": "execute",
            "parameters": {
                "command": [
                    "python",
                    "-c",
                    "import pyautogui; import time; pyautogui.click(960, 540); time.sleep(0.5);"
                ]
            }
        }
    ]

    obs = env.reset(task_config=example)

    if popup == "true":
        obs = process_image_with_popup(obs, example["popup_text"])
    done = False
    step_idx = 0
    # env.controller.start_recording()
    while not done and step_idx < max_steps:
        response, actions = agent.predict(
            instruction,
            obs
        )
        for action in actions:
            # Capture the timestamp before executing the action
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Step %d: %s", step_idx + 1, action)
            # obs, reward, done, info = env.step(action, args.sleep_after_execution)
            # if popup == "true":
            #     obs = process_image_with_popup(obs, example["popup_text"])
            # logger.info("Reward: %.2f", reward)
            # logger.info("Done: %s", done)
            # Save screenshot and trajectory information
            # with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
            #           "wb") as _f:
            #     _f.write(obs['screenshot'])
            with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action_timestamp": action_timestamp,
                    "action": action,
                    "response": response
                }))
                f.write("\n")
            # if done:
            #     agent.reset()
            #     logger.info("The episode is done.")
            #     break
        step_idx += 1
    # result = env.evaluate()
    # logger.info("Result: %s", result)  # 适用于列表
    # if isinstance(result, int):
    #     result = str(result)
    #
    # scores.append(result)
    #
    # result_str = " ".join(map(str, result))
    # with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
    #     f.write(result_str + "\n")
    # env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))


    shutil.rmtree("screenshot", ignore_errors=True)
    os.makedirs("screenshot", exist_ok=True)



def run_single_example_safety(agent, env, example, max_steps, instruction, args, example_result_dir, scores, popup):
    runtime_logger = setup_logger(example, example_result_dir)
    agent.reset(runtime_logger)
    example["config"].insert(0, {
        "type": "execute",
        "parameters": {
            "command": "xdotool search --onlyvisible . windowkill %@",
            "shell": True
        }
    })

    obs = env.reset(task_config=example)

    if popup == "true":
        obs = process_image_with_popup(obs, example["popup_text"])
    done = False
    step_idx = 0
    env.controller.start_recording()
    while not done and step_idx < max_steps:
        response, actions = agent.predict(
            instruction,
            obs
        )
        for action in actions:
            # Capture the timestamp before executing the action
            action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            logger.info("Step %d: %s", step_idx + 1, action)
            obs, reward, done, info = env.step(action, args.sleep_after_execution)
            if popup == "true":
                obs = process_image_with_popup(obs, example["popup_text"])
            logger.info("Reward: %.2f", reward)
            logger.info("Done: %s", done)
            # Save screenshot and trajectory information
            with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
                      "wb") as _f:
                _f.write(obs['screenshot'])
            with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
                f.write(json.dumps({
                    "step_num": step_idx + 1,
                    "action_timestamp": action_timestamp,
                    "action": action,
                    "reward": reward,
                    "done": done,
                    "info": info,
                    "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
                }))
                f.write("\n")
            if done:
                agent.reset()
                logger.info("The episode is done.")
                break
        step_idx += 1
    result = env.evaluate()
    logger.info("Result: %s", result)  # 适用于列表
    if isinstance(result, int):
        result = str(result)

    scores.append(result)

    result_str = " ".join(map(str, result))
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(result_str + "\n")
    env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))


    shutil.rmtree("screenshot", ignore_errors=True)
    os.makedirs("screenshot", exist_ok=True)


def run_single_example_os_copliot(agent, env, example, max_steps, instruction, args, example_result_dir, scores, popup):
    runtime_logger = setup_logger(example, example_result_dir)
    agent.reset(runtime_logger)
    env.controller.start_recording()
    # example["config"].append({
    #     "type": "execute",
    #     "parameters": {
    #         "command": "cd /home/user/Desktop/CODE/OS-Copilot-main && python task_run.py --task \"{}\"".format(
    #             example["dangerous_attack_question"]),
    #         "shell": True
    #     }
    # })
    example["config"].insert(0, {
        "type": "execute",
        "parameters": {
            "command": (
                "mv /home/user/Desktop/CODE/OS-Copilot-main/temp_logs/*.txt "
                "/home/user/Desktop/CODE/OS-Copilot-main/logs/ && "
                "rm -f /home/user/Desktop/CODE/OS-Copilot-main/temp_logs/*"
            ),
            "shell": True
        }
    })

    example["config"].insert(0, {
        "type": "execute",
        "parameters": {
            "command": "xdotool search --onlyvisible . windowkill %@",
            "shell": True
        }
    })

    example["config"].append({
        "type": "execute",
        "parameters": {
            "command": (
                f"echo \"{example['dangerous_attack_question']}\" "
                "> /home/user/Desktop/CODE/OS-Copilot-main/dangerous_attack_question.txt"
            ),
            "shell": True
        }
    })

    example["config"].append({
        "type": "execute",
        "parameters": {
            "command": (
                f"touch /home/user/Desktop/CODE/OS-Copilot-main/temp_logs/{example['id']}.txt"
            ),
            "shell": True
        }
    })
    example["config"].append({
        "type": "execute",
        "parameters": {
            "command": [
                "python",
                "-c",
                (
                    "import pyautogui; import time; "
                    "time.sleep(2); "
                    "pyautogui.hotkey('ctrl', 'alt', 't'); "  
                    "time.sleep(0.5); "
                    "pyautogui.typewrite('export all_proxy=NONE&&');"
                    "pyautogui.typewrite('cd /home/user/Desktop/CODE/OS-Copilot-main && python task_run.py');"
                    "pyautogui.press('enter')"
                )
            ]
        }
    })

    # example["config"].append({
    #             "type": "execute",
    #             "parameters": {
    #                 "command": "export all_proxy = ''",
    #                 "shell": True
    #             }
    #         })
    # example["config"].append({
    #     "type": "execute",
    #     "parameters": {
    #         "command": [
    #             "python",
    #             "-c",
    #             (
    #                 "import pyautogui; import time; "
    #                 "time.sleep(2); "
    #                 "pyautogui.hotkey('ctrl', 'alt', 't'); "
    #                 "time.sleep(0.5); "
    #                 "pyautogui.typewrite('cd /home/user/Desktop/CODE/OS-Copilot-main');"
    #                 f"pyautogui.typewrite('python task_run.py --task \"{example['dangerous_attack_question']}\"')"
    #                 "pyautogui.press('enter')"
    #             )
    #         ]
    #     }
    # })

    obs = env.reset(task_config=example)
    time.sleep(120)

    done = True
    step_idx = 0

    # while not done and step_idx < max_steps:
    #     response, actions = agent.predict(
    #         instruction,
    #         obs
    #     )
    #     for action in actions:
    #         # Capture the timestamp before executing the action
    #         action_timestamp = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
    #         logger.info("Step %d: %s", step_idx + 1, action)
    #         obs, reward, done, info = env.step(action, args.sleep_after_execution)
    #         if popup == "true":
    #             obs = process_image_with_popup(obs, example["popup_text"])
    #         logger.info("Reward: %.2f", reward)
    #         logger.info("Done: %s", done)
    #         # Save screenshot and trajectory information
    #         with open(os.path.join(example_result_dir, f"step_{step_idx + 1}_{action_timestamp}.png"),
    #                   "wb") as _f:
    #             _f.write(obs['screenshot'])
    #         with open(os.path.join(example_result_dir, "traj.jsonl"), "a") as f:
    #             f.write(json.dumps({
    #                 "step_num": step_idx + 1,
    #                 "action_timestamp": action_timestamp,
    #                 "action": action,
    #                 "reward": reward,
    #                 "done": done,
    #                 "info": info,
    #                 "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
    #             }))
    #             f.write("\n")
    #         if done:
    #             logger.info("The episode is done.")
    #             break
    #     step_idx += 1
    result = env.evaluate()
    logger.info("Result: %s", result)

    scores.append(result)

    result_str = " ".join(map(str, result))
    with open(os.path.join(example_result_dir, "result.txt"), "w", encoding="utf-8") as f:
        f.write(result_str + "\n")
    env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))


    shutil.rmtree("screenshot", ignore_errors=True)
    os.makedirs("screenshot", exist_ok=True)


def setup_logger(example, example_result_dir):
    runtime_logger = logging.getLogger(f"desktopenv.example.{example['id']}")
    runtime_logger.setLevel(logging.DEBUG)
    runtime_logger.addHandler(logging.FileHandler(os.path.join(example_result_dir, "runtime.log")))
    return runtime_logger
