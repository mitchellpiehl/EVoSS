import math
import sys
import openai

# key obtained by openai to access their API
openai.api_key = "sk-*****"

# Turns any value into a float if possible
def floatify(value):
    try: 
        value = float(value)
    except: 
        value = 0
    return value

# Checks to make sure a string has returned from the API
def check_string(s):
    if s == "":
        raise ValueError("Empty string encountered.")

# Calls the OpenAI API and sends in the prompt, model and max length, returns the response from the API 
def get_response(prompt, model, max_length):
    if model== 'gpt-3.5-turbo':
        completion = openai.ChatCompletion.create(model=model, messages=[{"role": "user", "content": f"{prompt}"}], max_tokens=max_length, temperature=0.4)
        response = completion.choices[0].message.content
        try:
            check_string(response)
        except Exception as e:
            print(e) 
            sys.exit(1)
        return response

# Checks to see if two floats are close to each other
def equals(pred, gold):
    difference = 0.09
    return (math.isclose(gold, pred, rel_tol=difference, abs_tol=difference))

# Used to verify if the estimate is close enough to the obtained answer
def verify(estimate, answer, alpha = 0.5):
    ret = False
    if estimate > 0:
        if (estimate * (1 - alpha)  < answer) and (estimate * (1 + alpha) > answer): 
            ret = True
        # sometimes estimate values are correct, the LLM just answers in thousands
        elif ((estimate *1000) * (1 - alpha)  < (answer)) and ((estimate * 1000) * (1 + alpha) > (answer)):
            ret = True
    else:
        if (estimate * (1 - alpha)  > answer) and (estimate * (1 + alpha) < answer): 
            ret = True
    return ret

# Takes a value and removes the unnecessary characters that may be added 
def cleanse_result(value):
    if isinstance(value, str):
        value = value.strip()
        value = value.replace(',', '')
        value = value.replace('$', '')
        value = value.replace('/', '')
        value = value.replace('#', '')
        value = value.replace(':', '')
        if value[-1]=='.':
            value = value[:-1]
        values = value.split(' ')
        if values[0] != value:
            for val in values:
                if val.isdigit():
                    value = val
                    break
        if value[0] != '-':
            values = value.split('-')
            if values[0] != value:
                for val in values:
                    if val.isdigit():
                        value = val
                        break
    return value
