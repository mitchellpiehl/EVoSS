import time
from utils import get_response, cleanse_result, verify, floatify, equals
from sympy import solve, parse_expr, sympify, Symbol
from sympy.parsing.sympy_parser import standard_transformations, implicit_multiplication_application, convert_xor
import numpy as np
import string
import re

# Sleep time used to take breaks to not overwhelm the API, keys can only be used a certain amount
sleep_time = 10
# prints results if set to true
print_results = True

# Uses GPT to decompose the question into statements, 2 shot prompting is used
def decomposition(statements, asking_part, model, max_length):
    prompt = f"""
            Statements: {statements}
            Question: {asking_part}
            ONLY Decompose these statements, do not answer the question.
            Make it as specific as possible towards answering the question.
            Include all details neccessary, and seperate the individual statements with "|" 

            An Example: 
            Statements: Mary had 5 apples. The next morning, she ate 2 apples. 
            Then, in the afternoon, she bought as many apples as she had after eating those apples in the morning. 
            Questions: How many apples did she end up with?

            Decomposition: 
            Mary initially had 5 apples.|
            The subsequent morning, Mary consumed 2 apples.|
            In the afternoon of the same day, Mary bought a quantity of apples equal to the amount she had remaining after her morning consumption.

            Another example: 
            Statements: The planet Goob completes one revolution after every 2 weeks.
            Question: How many hours will it take for it to complete half a revolution?

            Decomposition:
            The planet Goob completes one revolution after every 2 weeks. | There are 168 hours in a week 
            """
    decomposed = get_response(prompt = prompt, model = model, max_length = max_length)
    if print_results:
        print(f'Decomposition: {decomposed}')
    time.sleep(sleep_time)
   
    return decomposed

# Uses GPT to find an estimation of the correct answer
def estimation(statements, asking_part, model, max_length):
    prompt = f"""
            Statements: {statements} 
            Question: {asking_part}
            Q:  Use the statements to find a rough estimation of the right answer.
            Don't make it complicated, just find an answer that is close. Explain your reasoning.
            End your response with 'The answer is: X' 
            Where X is only an arabic numeral with no label:
            """
    response = get_response(prompt=prompt, model=model, max_length=max_length)
    if print_results:
        print(f'Estimation: {response}')
    time.sleep(sleep_time)
    llm_output = response.split(": ")
    value = llm_output[-1]
    
    if print_results:
        print(f'Estimated Numerical Answer: {value}')
    value = cleanse_result(value)
    return value

# Uses GPT to find an answer as a rectification if verification fails
def rectification(statements, asking_part, model, max_length, estimate):
    prompt = f"""
            Find the answer to this question using the statements and explain your reasoning:
            Statements: {statements} 
            Question: {asking_part}
            The correct answer may be around {estimate}
            End your response with 'The answer is: X'
            Where X is an arabic numeral with no label:
              """
    value = get_response(prompt=prompt, model=model, max_length=max_length)
    if print_results:
        print(f'Rectification: {value}')

    llm_output = value.split(": ")
    value = llm_output[-1]

    if print_results:
        print(f'Rectified Answer: {value}')
    time.sleep(sleep_time)

    value = cleanse_result(value)
    return value

# Uses GPT to take percentages out of equations if they are found
def fix_percent(statement):
    prompt = f"""
                Fix this statement so there is no percent sign. Do not do anything else.

                For example:
                b + 150% of c

                Should be turned into:
                b + 1.5 * c

                Statement: {statement}
              """
    value = get_response(prompt=prompt, model="gpt-3.5-turbo", max_length=50)
    if print_results:
        print(f'Percentage cleaning: {value} vs {statement}')
    time.sleep(sleep_time)
    value = cleanse_result(value)
    return value

# Removes characters that cannot be present while using the symbolic solver
def clean_equation(eq):
    eq = eq.strip()
    eq = eq.replace('$', '')
    if len(eq) >= 1 and eq[-1] == '.':       
        eq = eq[:-1]
    eq = eq.replace(',', '')
    eq = eq.replace('|', '')
    eq = eq.replace(':', '')
    eq = eq.replace('<', '=') 
    eq = eq.replace('>', '=')
    eq = eq.replace('==', '=') 
    if eq.count('=') == 2:
        eq = eq
    else:
        eq = eq.split(' = ')
        eq_left = eq[0]
        eq_right = eq[-1]
        if '%' in eq_right:    
            match = re.match(r'(\d+)% of (\w+)', eq_right)
            if match: 
                percent = int(match.group(1)) / 100
                variable = match.group(2)
                eq_right = f"{percent} * {variable}"
            else:
                eq_right = fix_percent(eq_right)
        #if a variable is more than one character, limits the variable to only one character
        eq_left = eq_left.strip()
        eq = eq_left + " = " + eq_right
    return eq

# Creates a new equation list in a specific format
def reformat_equations(x):
    eq_list = []
    if len(x) >= 1:
        for eq in x:
            eq = eq.replace(',', '')
            eq = eq.replace('$', '')
            eq_list.append(eq[2 : -2])
    result = []
    for eq in eq_list:
        if 'eq' in eq: 
            result.append(eq[eq.index('eq') + 2:]) 
        elif 'answer' in eq:  
            result.append(eq[eq.index('answer') + 6:].strip() + ' = ?') 
    return result

# Uses GPT to find an answer from the equations if the symbolic solver can't find an answer
def get_final_using_llm(equation_list, model, max_length):
    prompt = f"""
                Find the answer to this equation list:
                Equation_list: {equation_list} 
                End your response with 'The answer is: X'
                Where X is an arabic numeral with no label:
              """
    value = get_response(prompt=prompt, model=model, max_length=max_length)

    llm_output = value.split(": ")
    value = llm_output[-1]

    if print_results:
        print(f'LLM Equation Answer: {value}')
    time.sleep(sleep_time)

    value = cleanse_result(value)
    return value

def sympify_parse(equations):
    return sympify(parse_expr(equations, transformations=(standard_transformations + (implicit_multiplication_application,) + (convert_xor,))))

# Uses symbolic solver Sympy to find an answer when given an equation list
def find_answer_using_sympy(equation_list):
    for i in range (len(equation_list)):
        equation = clean_equation(equation_list[i])
        equation_list[i] = equation

        # equations can't contain 5 letters in a row
        for char in range(len(equation)):
            if char < len(equation) - 4:
                if equation[char].isalpha() and equation[char+1].isalpha() and equation[char+2].isalpha() and equation[char+3].isalpha() and equation[char+4].isalpha():
                    return 'An equation contains too many letters'

    if print_results:        
        print("New equation list: ")
        print(equation_list)
            
    goal = None
    goal_expression_list = []

    # tries to extract a goal variable and solve the equation
    if equation_list[-1].split('=')[0].strip().isalpha() or len(equation_list[-1].split('=')[0].strip()) == 2:
        goal = equation_list[-1].split('=')[0].strip()
    elif '=' in equation_list[-1]:
        for letter in list(string.ascii_lowercase) + list(string.ascii_uppercase):
            if letter not in equation_list[-1]:
                goal = letter
                break

        if goal is None:
            return 'invalid goal equation'
        else:
            goal_expression = sympify_parse(goal + ' - (' + equation_list[-1].split('=')[0].strip() + ')')
            try:
                return float(solve(goal_expression)[0])
            except Exception as e:
                pass
            goal_expression_list.append(goal_expression)

    if len(equation_list) == 1:
        try:
            return float(sympify_parse(equation_list[0].split('=')[0]))
        except Exception as e:
            return 'invalid single equation'
        
    if goal == None:
        return 'no goal found'

    # if possible, contructs a system of equations and solves
    for i in range(len(equation_list) - 1):
        indi_eq = equation_list[i]  
        if '?' not in indi_eq:
            try:    
                indi_eq_split = indi_eq.split('=')
                new_eq = sympify_parse(indi_eq_split[0].strip() + ' - (' + indi_eq_split[1].strip() + ')')
            except Exception as e:
                return 'invalid equations'
            goal_expression_list.append(new_eq)

            try:
                try:
                    return float(solve(goal_expression_list)[Symbol(goal)])
                except Exception as e:
                    return float(solve(goal_expression_list)[0][Symbol(goal)])
            except Exception as e:
                pass

    return 'no solution'

# Uses GPT to create equations given a decomposition, uses 3 shot prompting based on the dataset used to help guide the GPT
def initialization(model, max_length, decomposed, asking_part, helper_statement, dataset):
    # uses few shot prompting to increase accuracy, provides rules examples and question in the form of statement/asking part
    if dataset == 'Trig300':
        prompt = f"""
        Let's create equations for mathematical word problems in a careful, formal manner. Your response should follow the Peano format:
        1- Each sentence in the solution either introduces a new variable or states a new equation with no symbols.
        2- The last sentence gives the goal: which variable will contain the answer to the problem.
        3- Each equation only uses previously introduced variables.
        4- All variables are only one character long. 
        5- Use all the numbers in the question.
        6- Each declared equation or variable should be encased with '[[' and ']]'
        7- The equations end with: "The answer is the value of d [[answer _]]."
        8- When using trigonmetry operations such as sin(x), cos(x) etc. x needs to be in radians. 
        9- Always answer in degrees instead of radians
        10- Only use these trigonmic operations: sin, cos, sec, tan, cot, asin, acsc, acos, asec, atan, acot
        11- ALWAYS use radians in your equations. If degrees are given or needed, do the proper conversions EVERY time.

        An Example: 
        Statements: The tree is known to be 276ft tall.|
        The angle of elevation to the sun is 36 degrees. 
        Question: What is the length of the shadow cast by the tree? 
        Peano solution:

        Let a be the height of the tree [[var a]]. We have [[eq a = 276]]. 
        Let b be the length of the shadow cast by the tree [[var b]].
        Let c be the angle of elevation to the sun in radians [[var c]]. We have [[eq c = 33 * pi / 180]]
        Since the angle of elevation to the sun forms a right triangle with the tree and its shadow, we have [[eq sin(c) = a / b]]. 
        The answer is the value of b [[answer b]]. 

        Another example:
        Statements: The boat is at a distance from the lighthouse. | The angle of depression is the angle between the line of sight to the object and the horizontal line. |
        The height of the lighthouse is 85 meters. |
        The angle of depression is 23 degrees. | The distance between the boat the lighthouse can be calculated using trigonometry.
        Question: How far from the boat is the top of the lighthouse?

        Peano solution:

        Let a be the height of the lighthouse [[var a]]. We have [[eq a = 85]]. 
        Let b be the distance between the boat and the lighthouse [[var b]].
        Let c be the angle of depression in radians [[var c]]. We have [[eq c = 23 * pi / 180]]. 
        Since the angle of depression forms a right triangle with the lighthouse, its height, and the distance to the boat, we have [[eq tan(c) = a / b]]. 
        The answer is the value of b [[answer b]].

        Another example:
        Statements: The distance from the base of the bungee jump platform is 124ft. | The angle of elevation to the platform is 72 degrees. |
        Question: Find the height of the platform

        Peano solution:

        Let a be the distance from the base of the bungee jump platform [[var a]]. We have [[eq a = 124]]. 
        Let b be the height of bungee jump platform [[var b]].
        Let c be the angle of elevation to the platform in radians [[var c]]. We have [[eq c = 72 * pi / 180]].
        Since the angle of elevation to the platform forms a right triangle with the distance and the height. We have [[eq tan(c) = b / a]].
        The answer is the value of b [[answer b]].

        Now follow the instructions and examples for this question: 
        Statements: {decomposed}
        Question: {asking_part}         
        """
    else:
        prompt = f"""
        Let's create equations for mathematical word problems in a careful, formal manner. Your response should follow the Peano format:
        1- Each sentence in the solution either introduces a new variable or states a new equation with no symbols.
        2- The last sentence gives the goal: which variable will contain the answer to the problem.
        3- Each equation only uses previously introduced variables.
        4- All variables are only one character long. 
        5- Each quantity is only named by one variable.
        6- Use all the numbers in the question.
        7- Each declared equation or variable should be encased with '[[' and ']]'
        8- The equations end with: "The answer is the value of d [[answer _]]."
        
        An Example: 
        Statements: Mary initially had 5 apples.|
        The subsequent morning, Mary consumed 2 apples.|
        In the afternoon of the same day, Mary bought a quantity of apples equivalent to the amount she had remaining after her morning consumption.
        Question: How many apples did she end up with?
        Peano solution:

        Let a be the number of apples Mary started with [[var a]]. We have [[eq a = 5]]. 
        Let b be how many apples she had in the morning after eating 2 apples [[var b]]. We have [[eq b = a - 2]]. 
        Let c be the apples she bought in the afternoon [[var c]]. 
        Since she bought as many as she had after eating, we have [[eq c = b]]. 
        Let d be how many apples she ended up with [[var d]]. We have [[eq d = b + c]]. 
        The answer is the value of d [[answer d]]. 

        Another example:
        Statements: The planet Goob completes one revolution after every 2 weeks. | There are 168 hours in a week 
        Question: How many hours will it take for it to complete half a revolution?

        Peano solution:

        Let a be the number of hours in a week [[var a]]. We have [[eq a = 168]]. 
        Let b be the number of hours in a revolution [[var b]]. We have [[eq b = a * 2]]. 
        Let c be the number of hours in half a revolution [[var c]]. We have [[eq c = b / 2]]. 
        The answer is the value of c [[answer c]].

        Another example:
        Statements: Shawn has five toys | For Christmas, he got two toys each from his mom and dad.
        Question: How many toys does he have now?

        Peano solution:

        Let a be the number of toys Shawn started [[var a]]. We have [[eq a = 5]]. 
        Let b be the number of toys Shawn got for Christmas from his mom [[var b]]. We have [[eq b = 2]].
        Let c be the number of toys Shawn got for Christmas from his dad [[var c]]. We have [[eq c = 2]].
        Let d be the number of toys Shawn has now [[var d]]. We have [[eq d = a + b + c]].
        The answer is the value of d [[answer d]].

        Now follow the instructions and examples for this question: 
        Statements: {decomposed}
        Question: {asking_part}         
        """
    
    prompt += helper_statement
    
    equations = get_response(prompt=prompt, model=model, max_length=max_length)

    if print_results:
        print(f'Initial Equations: {equations}')
    pattern1 = r'We have (\w+) = (.*?)(?=\.|$)'
    pattern2 = r'\[\[\s*(\w+)\s*=\s*(.*?)\s*\]'
    
    equations = re.sub(pattern1, lambda match: f"We have [[eq {match.group(1)} = {match.group(2)}]].", equations)
    equations = re.sub(pattern2, lambda match: f'[[{match.group(1)} = {match.group(2)}]]', equations)
    eq_list = re.findall(r'\[\[.*?\]\]', equations)
    missing_answers = re.findall(r'The answer is the value of (\w+)\s*(?!\[\[answer \w+\]\])', equations)

    for missing_answer in missing_answers:
        match = re.search(r'\w+', missing_answer)  # extract the variable name like 'd', 'e', 'f'
        if match and f"[[answer {match.group()}]]" not in eq_list and len({match.group()}) == 1:
            eq_list.append(f"[[answer {match.group()}]]")

    initial_answer = find_answer_using_sympy(reformat_equations(eq_list))
    
    if print_results:
        print(f'Numerical Answer: {initial_answer}')
    time.sleep(sleep_time)
    return initial_answer, equations

# Continues to call initiailiazation, adding helper prompts based on the error recieved until a numerical answer if found by SymPy
def check_answer(answer, model, max_length, asking_part, sentences, equations, dataset):
    iterations = 0
    while (isinstance(answer, str) and (iterations < 2)):
        helper_statement = (
            "Make sure no words are used in the actual equations" if answer == "An equation contains too many letters" else
            "Make sure [[answer _]] is included" if answer in ["invalid goal equation", "no goal found"] else
            "Make sure the equations are solveable and [[answer _]] is included" if answer == "no solution" else
            "Make sure the equations are solveable" if answer == "invalid equations 4" else
            "Make sure to follow all the rules"
        )
        answer, equations = initialization(model, max_length, sentences, asking_part, helper_statement, dataset)
        iterations += 1
    return answer, equations

# Generates equations, finds an answer from the equations, finds an estimate, compares the estimate to the answer and rectifies if needed
def iteration(answer, model, max_length, asking_part, sentences, equations, generated_answers, decomposed, iterate_value, dataset):
    answer, equations = check_answer(answer, model, max_length, asking_part, sentences, equations, dataset)
    if isinstance(answer, str):
        answer = floatify(get_final_using_llm(equations, model, max_length))

    generated_answers[f'check{iterate_value}'] = answer   

    estimate = floatify(estimation(decomposed, asking_part, model, max_length))
    generated_answers[f'estimate{iterate_value}'] = estimate

    if verify(estimate, answer):
        return answer, generated_answers
    else: 
        r_answer = floatify(rectification(sentences, asking_part, model, max_length, estimate))
        iterate_value += 1
        matches = False
        for value in generated_answers.values():
            float_value = floatify(value)
            if float_value is not 0 and equals(float_value, r_answer):
                matches = True
                answer = r_answer
                break
        generated_answers[f'rectified{iterate_value}'] = r_answer
        if matches == False:
            answer, generated_answers = pipeline(asking_part, sentences, model, max_length, generated_answers, iterate_value, dataset)
    return answer, generated_answers

# Start of process of finding an answer for each question, returns a generated answer list as well as the final answer
def pipeline(asking_part, sentences, model, max_length, generated_answers, iterate_value, dataset):
    helper_statement = ""
    decomposed = decomposition(sentences, asking_part, model, max_length)
    initital_answer, equations = initialization(model, max_length, decomposed, asking_part, helper_statement, dataset)

    if iterate_value == 0:
        generated_answers[f'initial{iterate_value}'] = initital_answer
        final_answer, generated_answers = iteration(initital_answer, model, max_length, asking_part, sentences, equations, generated_answers, decomposed, iterate_value, dataset)
    elif iterate_value < 3:
        matches = False
        for value in generated_answers.values():
            try:
                if equals(float(value), float(initital_answer)): 
                    matches = True
                    generated_answers[f'rectified{iterate_value}'] = initital_answer
            except ValueError:
                continue
        generated_answers[f'initial{iterate_value}'] = initital_answer
        if not matches:     
            final_answer, generated_answers = iteration(initital_answer, model, max_length, asking_part, sentences, equations, generated_answers, decomposed, iterate_value, dataset)
        else: 
            final_answer = initital_answer
    # if too many iterations have gone through without verification passing, just move on with the answer as check0
    else:
        final_answer = generated_answers['check0']

    if isinstance(final_answer, str):
        for value in generated_answers.values():
            try:
                float_value = float(value)
                final_answer = float_value
                break
            except ValueError:
                continue

    print("final answer: " + str(final_answer))
    return final_answer, generated_answers

# Used for testing SCoSS mentioned in the paper
def SCpipeline(asking_part, sentences, model, max_length, generated_answers):
    helper_statement = ""
    answers = []
    decomposed = decomposition(sentences, asking_part, model, max_length)
    for i in range(5):
        initital_answer, equations = initialization(model, max_length, decomposed, asking_part, helper_statement)
        generated_answers[f'initial{i}'] = initital_answer
        check, equations = check_answer(initital_answer, model, max_length, asking_part, sentences, equations)
        generated_answers[f'check{i}'] = check
        if isinstance(check, str):
            check = floatify(get_final_using_llm(equations, model, max_length))
        answers.append(check)
    mode = max(answers, key = answers.count)
    generated_answers['check0'], generated_answers['estimate0'] = 0, 0
    return mode, generated_answers
