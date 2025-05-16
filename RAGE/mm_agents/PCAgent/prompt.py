# PC
def get_action_prompt_OS_world(instruction, clickable_infos, width, height, thought_history, summary_history, action_history, last_summary, last_action, reflection_thought, add_info, error_flag, completed_content, memory, use_som, icon_caption, location_info):
    prompt = "### Background ###\n"
    if use_som == 1:
        prompt += f"The first image is a clean computer screenshot. Its width is {width} pixels and its height is {height} pixels. And the second image is the annotated version of it, where icons are marked with numbers."
    else:
        prompt += f"This image is a computer screenshot. Its width is {width} pixels and its height is {height} pixels."
    
    prompt += "### Screenshot information ###\n"
    prompt += "In order to help you better perceive the content in this screenshot, we extract some information of the current screenshot. "
    prompt += "This information consists of two parts: coordinates; content. "
    if location_info == 'center':
        prompt += "The format of the coordinates is [x, y], x is the pixel from left to right and y is the pixel from top to bottom; "
    elif location_info == 'bbox':
        prompt += "The format of the coordinates is [x1, y1, x2, y2], x is the pixel from left to right and y is the pixel from top to bottom. (x1, y1) is the coordinates of the upper-left corner, (x2, y2) is the coordinates of the bottom-right corner; "

    if icon_caption == 1:
        prompt += "the content is a text or an icon description respectively. "
    else:
        prompt += "the content is a text or 'icon' respectively. "
    prompt += "The information is as follow:\n"

    for clickable_info in clickable_infos:
        if clickable_info['text'] != "" and clickable_info['text'] != "icon: None" and clickable_info['coordinates'] != (0, 0):
            prompt += f"{clickable_info['coordinates']}; {clickable_info['text']}\n"
            # print(f"{clickable_info['coordinates']}; {clickable_info['text']}\n")
    
    prompt += "Please note that this information is not necessarily accurate. You need to combine the screenshot to understand."
    prompt += "\n\n"
    
    if len(action_history) > 0:
        prompt += "### History operations ###\n"
        prompt += "Before arriving at the current screenshot, you have completed the following operations:\n"
        # prompt += "Before reaching this page, some operations have been completed. You need to refer to the completed operations and the corresponding thoughts to decide the next operation. These operations are as follow:\n"
        for i in range(len(action_history)):
            prompt += f"Step-{i+1}: [Operation: " + summary_history[i].split(' to ')[0].strip() + "; Action: " + action_history[i] + "]\n"
            # prompt += f"Step-{i+1}: [Thought: " + thought_history[i] + "; Operation: " + summary_history[i].split(" to ")[0].strip() + "; Action: " + action_history[i] + "]\n"
            # print("Step-{i+1}: [Operation: " + summary_history[i].split(' to  ')[0].strip() + "; Action: " + action_history[i] + "]\n")
        prompt += "\n"
    
    if completed_content != "":
        prompt += "### Progress ###\n"
        prompt += "After completing the history operations, you have the following thoughts about the progress of user\'s instruction completion:\n"
        prompt += "Completed contents:\n" + completed_content + "\n\n"
    
    if memory != "":
        prompt += "### Memory ###\n"
        prompt += "During the operations, you record the following contents on the screenshot for use in subsequent operations:\n"
        prompt += "Memory:\n" + memory + "\n"
    
    if reflection_thought != "":
        prompt += "### The reflection thought of the last operation ###\n"
        prompt += reflection_thought
        prompt += "\n\n"

    if error_flag:
        prompt += "### Last operation ###\n"
        prompt += f"You previously wanted to perform the operation \"{last_summary}\" on this page and executed the Action \"{last_action}\". But you find that this operation does not meet your expectation. You need to reflect and revise your operation this time."
        prompt += "\n\n"
        print(f"You previously wanted to perform the operation \"{last_summary}\" on this page and executed the Action \"{last_action}\". But you find that this operation does not meet your expectation. You need to reflect and revise your operation this time.")

    
    # prompt += "### Output requirements ###\n"
    # prompt += "You need to output the following content:\n"

    prompt += "### Output format ###\n"
    prompt += "### Thought ###\nThis is your thinking about how to proceed the next operation, please output the thoughts about the history operations explicitly.\n"
    # prompt += ("### Action ###\n  Follow the format and choose the correct action type and parameters in the format in 'ACTION_SPACE' in SYSTEM_PROMPT. "
    #            "REMEMBER: Yu should only RETURN ME THE action_type AND parameters I ASKED FOR. NEVER EVER RETURN ME ANYTHING ELSE. You MUST wrap the dict with backticks (\`). You MUST choose and ONLY CHOOSE from the action space, otherwise your action will be considered as invalid and you will get a penalty.\n")
    format = f"""
    Follow the format in SYSTEM_PROMPT. You ONLY need to return the code inside a code block, like this:
    ```python
    # your code here
    ```") """
    action_pro = "### Action ###\n"  + format

    prompt += (action_pro)





    prompt += "### Operation ###\nThis is a one sentence summary of this operation."
    prompt += "\n\n"

    # prompt += "Your output consists of the following three parts:\n"
    # prompt += "### Thought ###\nThink about the requirements that have been completed in previous operations and the requirements that need to be completed in the next one operation.\n"
    # prompt += "### Action ###\nYou can only choose one from the actions above. Make sure to generate the coordinates or text in the \"()\".\n"
    # prompt += "### Summary ###\nPlease generate a brief natural language description for the operation in Action based on your Thought."

    if add_info != "":
        prompt += "### Hint ###\n"
        prompt += "There are hints to help you complete the user\'s instructions. The hints are as follow:\n"
        prompt += add_info
        prompt += "\n\n"

    return prompt


def get_reflect_prompt(instruction, clickable_infos1, clickable_infos2, width, height, summary, action, add_info):
    prompt = f"These images are two computer screenshots before and after an operation. Their widths are {width} pixels and their heights are {height} pixels.\n\n"
    
    prompt += "In order to help you better perceive the content in this screenshot, we extract some information on the current screenshot. "
    prompt += "The information consists of two parts, consisting of format: coordinates; content. "
    prompt += "The format of the coordinates is [x, y], x is the pixel from left to right and y is the pixel from top to bottom; the content is a text or an icon description respectively "
    prompt += "\n\n"
    
    prompt += "### Before the current operation ###\n"
    prompt += "Screenshot information:\n"
    for clickable_info in clickable_infos1:
        if clickable_info['text'] != "" and clickable_info['text'] != "icon: None" and clickable_info['coordinates'] != (0, 0):
            prompt += f"{clickable_info['coordinates']}; {clickable_info['text']}\n"
    prompt += "\n\n"
            
    prompt += "### After the current operation ###\n"
    prompt += "Screenshot information:\n"
    for clickable_info in clickable_infos2:
        if clickable_info['text'] != "" and clickable_info['text'] != "icon: None" and clickable_info['coordinates'] != (0, 0):
            prompt += f"{clickable_info['coordinates']}; {clickable_info['text']}\n"
    prompt += "\n\n"
    
    prompt += "### Current operation ###\n"
    prompt += f"The user\'s instruction is: {instruction}."
    if add_info != "":
        prompt += f"You also need to note the following requirements: {add_info}."
    prompt += "In the process of completing the requirements of instruction, an operation is performed on the computer. Below are the details of this operation:\n"
    prompt += "Operation thought: " + summary.split(" to ")[0].strip() + "\n"
    prompt += "Operation action: " + action
    prompt += "\n\n"
    
    prompt += "### Response requirements ###\n"
    prompt += "Now you need to output the following content based on the screenshots before and after the current operation:\n"
    prompt += "Whether the result of the \"Operation action\" meets your expectation of \"Operation thought\"?\n"
    prompt += "A: The result of the \"Operation action\" meets my expectation of \"Operation thought\".\n"
    prompt += "B: The \"Operation action\" results in a wrong page and I need to do something to correct this.\n"
    prompt += "C: The \"Operation action\" produces no changes."
    prompt += "\n\n"
    
    prompt += "### Output format ###\n"
    prompt += "Your output format is:\n"
    prompt += "### Thought ###\nYour thought about the question\n"
    prompt += "### Answer ###\nA or B or C"
    
    return prompt


def get_memory_prompt(insight):
    if insight != "":
        prompt  = "### Important content ###\n"
        prompt += insight
        prompt += "\n\n"
    
        prompt += "### Response requirements ###\n"
        prompt += "Please think about whether there is any content closely related to ### Important content ### on the current page? If there is, please output the content. If not, please output \"None\".\n\n"
    
    else:
        prompt  = "### Response requirements ###\n"
        prompt += "Please think about whether there is any content closely related to user\'s instrcution on the current page? If there is, please output the content. If not, please output \"None\".\n\n"
    
    prompt += "### Output format ###\n"
    prompt += "Your output format is:\n"
    prompt += "### Important content ###\nThe content or None. Please do not repeatedly output the information in ### Memory ###."
    
    return prompt

def get_process_prompt(instruction, thought_history, summary_history, action_history, completed_content, add_info):
    prompt = "### Background ###\n"
    prompt += f"There is an user\'s instruction which is: {instruction}. You are a computer operating assistant and are operating the user\'s computer.\n\n"

    if add_info != "":
        prompt += "### Hint ###\n"
        prompt += "There are hints to help you complete the user\'s instructions. The hints are as follow:\n"
        prompt += add_info
        prompt += "\n\n"
    
    if len(thought_history) > 1:
        prompt += "### History operations ###\n"
        prompt += "To complete the requirements of user\'s instruction, you have performed a series of operations. These operations are as follow:\n"
        for i in range(len(summary_history)):
            operation = summary_history[i].split(" to ")[0].strip()
            prompt += f"Step-{i+1}: [Operation thought: " + operation + "; Operation action: " + action_history[i] + "]\n"
        prompt += "\n"
        
        prompt += "### Progress thinking ###\n"
        prompt += "After completing the history operations, you have the following thoughts about the progress of user\'s instruction completion:\n"
        prompt += "Completed contents:\n" + completed_content + "\n\n"
        
        prompt += "### Response requirements ###\n"
        prompt += "Now you need to update the \"Completed contents\". Completed contents is a general summary of the current contents that have been completed based on the ### History operations ###.\n\n"
        
        prompt += "### Output format ###\n"
        prompt += "Your output format is:\n"
        prompt += "### Completed contents ###\nUpdated Completed contents. Don\'t output the purpose of any operation. Just summarize the contents that have been actually completed in the ### History operations ###."
        
    else:
        prompt += "### Current operation ###\n"
        prompt += "To complete the requirements of user\'s instruction, you have performed an operation. Your operation thought and action of this operation are as follows:\n"
        prompt += f"Operation thought: {thought_history[-1]}\n"
        operation = summary_history[-1].split(" to ")[0].strip()
        prompt += f"Operation action: {operation}\n\n"
        
        prompt += "### Response requirements ###\n"
        prompt += "Now you need to combine all of the above to generate the \"Completed contents\".\n"
        prompt += "Completed contents is a general summary of the current contents that have been completed. You need to first focus on the requirements of user\'s instruction, and then summarize the contents that have been completed.\n\n"
        
        prompt += "### Output format ###\n"
        prompt += "Your output format is:\n"
        prompt += "### Completed contents ###\nGenerated Completed contents. Don\'t output the purpose of any operation. Just summarize the contents that have been actually completed in the ### Current operation ###.\n"
        prompt += "(Please use English to output)"
        
    return prompt