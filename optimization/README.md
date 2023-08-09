<div align= "center">
    <h1> DB-GPT: A Not-Only-LLM Database Toolkit</h1>
</div>

Welcome to the DB-GPT code repository! Our framework is based on LLM and designed to facilitate database tasks. We have conducted preliminary experiments to validate its performance and hopefully contribute to its development together.

## Setup

```shell
conda create -n LMDB python=3.9
conda activate LMDB
while read requirement; do pip install $requirement; done < requirements.txt
```

## Initial Implementation
First, we generate the instruction from a small number of collected samples (splitting into training and evaluation sets), i.e., deriving several instructions using the LLM on training set and choosing the best instruction by evaluating on evaluation set. Second, based on the task requirements, we collect other input features such as demonstration examples (e.g., query rewriting pairs) and data statistics (e.g., distinct value ratios of the columns). Finally, we concatenate the instruction, collected features, and the input into a prompt sequence, and rely on the LLM to output desired results based on the prompt sequence.

## Modules

The description of files included in each module is shown below (click corresponding links to view detailed instructions).


| Module              | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| [nl2sql](https://github.com/OpenBMB/BMTools/tree/main/bmtools/tools/database) | The implementation of requesting database tuples via natural language.        |
| [query_rewrite](./query_rewrite) | The implementation of LLM for query rewrite.        |
| [index_tuning](./index_tuning) | The implementation of LLM for index tuning.        |
| [anomaly_diagnosis](https://github.com/zhouxh19/AgentVerse_for_Database_Diagnosis) (multi-llm) | The implementation of diagnosing root causes of database anomalies.        |
| automatic_prompt_engineer | Instruction induction method [APE](https://github.com/keirp/automatic_prompt_engineer), which uses in-context capability of LLM to generate instructions. |
| tool_learning | The implementation of LLM-based tool learning ([bmtools](https://github.com/OpenBMB/BMTools)) for database.        |
| evaluation | Evaluation methods of database tasks. |
| utils | Reusable functional modules among different tasks and algorithms. |

## Contributing
Please leave your comments in the Issues if you would like to get involved or contribute!
