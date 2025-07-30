

---

````markdown
# Agent

## Prompt-based Agents

### Supported Models

Our agent framework supports a wide range of foundational and multimodal models:

#### Proprietary Models

- **OpenAI GPT Models**:  
  - GPT-3.5 (`gpt-3.5-turbo-16k`, etc.)  
  - GPT-4 (`gpt-4-0125-preview`, `gpt-4-1106-preview`, etc.)  
  - GPT-4V (`gpt-4-vision-preview`)  
  - GPT-o3 (`o` series)

- **Google Gemini Models**:
  - Gemini-1.5 Pro  
  - Gemini-2.0 Flash

- **Anthropic Claude Models**:  
  - Claude 2  
  - Claude 3 (`claude-3-haiku-2024030`, `claude-3-sonnet-2024022`, etc.)

#### Open-Source Models

- **Mistral**: Mixtral 8x7B and variants  
- **Qwen**: `Qwen` 
- **CogAgent**  
- **Meta LLaMA 3**: `llama3-70b`  
- **DeepSeek**  
- **THUDM/Cogagent**  


---

### How to Use

```python
from mm_agents.agent import PromptAgent

agent = PromptAgent(
    model="gpt-4-vision-preview",
    observation_type="screenshot",
)
agent.reset()

instruction = "Please help me to find the nearest restaurant."
obs = {
    "screenshot": open("path/to/observation.jpg", 'rb').read()
}
response, actions = agent.predict(
    instruction,
    obs
)
````

---

### Observation Space

We support the following observation types:

* `screenshot`: Screenshot of the current screen
* `a11y_tree`: Accessibility tree in XML format (linearized)
* `screenshot_a11y_tree`: Combination of screenshot and accessibility tree
* `som`: Set-of-Mark representation with bounding boxes and metadata

---

### Action Space

Two formats are supported:

* `pyautogui`: Python-based control scripts (mouse/keyboard)
* `computer_13`: Enumerated discrete actions for desktop automation

---

### Feeding Observations

```python
obs = {
    "screenshot": open("path/to/observation.jpg", 'rb').read(),
    "accessibility_tree": "<accessibility tree XML string>"
}
response, actions = agent.predict(
    instruction,
    obs
)
```

---

### Agent Variants

* `PromptAgent`: Standard agent that parses and executes actions
* `PromptAgentwoaction`: Variant that can reason or generate outputs without executing actions

---

### Features

* Multimodal prompt support (image + text tree)
* Automatic parsing of LLM outputs (code or action)
* History-aware predictions (trajectory support)
* Retry logic for resilient model calls
* Support for both cloud and local LLMs

---

---

