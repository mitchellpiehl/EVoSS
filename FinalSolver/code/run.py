import warnings
warnings.filterwarnings('ignore')
import json
import argparse
from tqdm import tqdm
from prompt import pipeline


parser = argparse.ArgumentParser(description="Index of dataset")
parser.add_argument('--data_index', type=int, required=True, metavar='', default=2, help="0: 'SVAMP', 1: 'GSM8K', 2: 'Algebra', 3: 'NewSVAMP', 4: 'Trig300'")
args = parser.parse_args()

datasets = ['SVAMP', 'GSM8K', 'Algebra', 'NewSVAMP', 'Trig300']
data_name = datasets[args.data_index]


with open(f'../data/{data_name}.json', 'r') as f:
    samples = json.load(f)
file_path = f'../results/{data_name}.txt'

if data_name == 'Algebra':
    problems = [sample['question'] for sample in samples]
    g_answers = [sample['final_answer'] for sample in samples]
elif data_name == 'NewSVAMP':
    problems = [str(sample['Body']) + ' ' + str(sample['Question']) for sample in samples]
    g_answers = [sample['Answer'] for sample in samples]
elif data_name == 'Trig300':
    problems = [sample['Question'] for sample in samples]
    g_answers = [sample['Answer'] for sample in samples]
else:
    problems = [sample['problem'] for sample in samples]
    g_answers = [sample['gold_answer'] for sample in samples]


# Setting parameters for OpenAI api
prompt_strategy = 'EVoSS'
model_name = "gpt-3.5-turbo"
max_length = 256


add_idx = 0
# goes through each problem in the selected dataset and sends the needed information to pipeline in prompt.py, a final answer is returned and saved to a .txt file
for problem_idx in tqdm(range(len(samples)), desc=f'{data_name} {prompt_strategy} {model_name}'):
     
    problem_idx += add_idx
    problem = problems[problem_idx]
    
    # splits the sentences takes the last sentences as the asking part. Every single questions asking part is the last question
    sentences = problem.split(". ")
    asking_part = sentences[-1]
    sentences.pop()

    # creates a generated answer dictionary to append all the answers generated per problem
    generated_answers = {}
    iterate_value = 0

    # finds the final answer
    final_answer, generated_answers = pipeline(asking_part, sentences, model_name, max_length, generated_answers, iterate_value, data_name)
    generated_answers['final_answer'] = final_answer
    generated_answers['gold'] = g_answers[problem_idx]

    # saves the final answer and the gold answer into a .txt file 
    with open(file_path, 'a') as file:
        for key, value in generated_answers.items():
            file.write(f'{key}: {value}\n')
        file.write('\n')
