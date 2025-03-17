# CHAINSENTRY

Towards Automated SOC Alert Validation: Leveraging LLMs for False Positives Identification

## Setup

### Python

```
conda create python=3.10 --name chainsentry
conda activate chainsentry
pip install -r chainsentry_requirements.txt
```

### Setting Environment Variables

1. Directly setting `Openai_key`in tools/gpt_con.py

   ```
               try:
                   client = OpenAI(api_key="", base_url="")
                   if user2prompt == "":
   ```

2. Setting vt key in `scripts/ana_tools/vt_search.py`

   ```
   vt_key = ""
   ```

## Running Instructions

​	1.	Set the working directory to the root of **ChainSentry**:

```
export PYTHONPATH=/path/to/your/CHAINSENTRY
```

​	2.	Execute alertgpt_v1.py:

```
python alertgpt_v1.py
```

To change the model or test dataset path, modify the respective settings directly in alertgpt_v1.py.

# Test set & Comparison Methods

## Test set

- NGIDS_DS_1000_modified.json: NGIDS-DS
- combined_unique_data_tp.json: GSI-Data<sub>TT</sub>
- combined_unique_data_fp.json: GSI-Data<sub>BE</sub>

## Comparison Methods

The code and prompts for the comparison method are in `scripts/compare_prompt.py`

