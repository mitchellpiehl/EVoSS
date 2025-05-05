# EVoSS
Solving Math Word Problems Using Estimation Verification
This code is associated with the paper I wrote in 2024 titled "Solving Math Word Problems Using Estimation Verification and Equation Generation" that can be found at this link:
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5166090

The purpose of this project was to research novel ways to improve the abilites of large language models abilities to solve math word problems. I experimented with many different ideas and created this program that uses an idea similar to concepts in mathematics education that involve ensuring answer accuracy using estimation as a form of verification. This process improves current state of the art results by an average of 2 percent across popular math word problem datasets. For more information of details and results, please read my paper found at the link above. 

To run the code, you will need to pip install the requirements.txt file; do so in a Conda environment in order to save the packages in a directory that will not affect other programs. Then you can run the program by navigating to the code folder and executing:

python3 run.py --data_index 1

The data index to use to run the given data files are as follows:
0: 'SVAMP'
1: 'GSM8K'
2: 'Algebra’ 
3: 'SVAMPClean'
4: 'Trig300'

Before running, you will need to obtain a key from OpenAI in order to use the API, and then insert the key in the utils.py file where it says: 
openai.api_key = "sk-***"


