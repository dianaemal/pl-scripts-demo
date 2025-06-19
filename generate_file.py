import re
from jinja2 import Template
import html
import os
import requests
import subprocess 
import time
import shutil
import json
import uuid
import argparse

#Define the Question class that holds all the data for a single question
class Question:

    def __init__(self, id, question, options, title, topic, tags, answer=None, type=None):

        self.uuid = self.generate_uuid() # Assign a unique id to each question instance
        self.type = type  # The question type (e.g., 'MCQ', 'String Input')
        self.id = id # The question ID 
        self.question = question # The question text
        self.options = options # is a dictionary like: {A: '', B: ''...}
        self.title = title 
        self.topic = topic
        self.tags = tags # Comma-separated tags for the question
        self.answer = answer # correct answer for string input questions

    # For debugging: show key info about the question
    def __repr__(self):
        return f"<Question id='{self.id}' title='{self.options}' question='{self.question}' answer={self.answer}>"

    # Function to generate a UUID using an external API
    def generate_uuid(self):
        generated_uuid = str(uuid.uuid4())
        print(f"Generated UUID: {generated_uuid}")  # Debugging print
        return generated_uuid
                
    # Function to create a context dictionary for rendering templates            
    def create_context(self):
        context = {}
        i = 1
         # Handle "___" if the question has a fill-in-the-blank style
        if "___" in self.question:
            question1, question2 = self.question.split("___")
            context["question1"] = question1.strip()
            context["question2"] = question2.strip()
        else:
            # For other questions, just use the whole question text
            context["question"] = self.question.strip()

        # Add the title, topic, type, id, and uuid to the context
        context["title"] = self.title
        context["topic"] = self.topic
        context["type"] = self.type
        context["id"] = self.id
        context["uuid"] = self.uuid
        if self.type == 'String Input':
            # Only String Input questions need the answer in the context
            context["answer"] = self.answer

        # Add the tags to the context, converting them to a JSON string
        context["tags"] = json.dumps(self.tags.split(", "))
        i = 1
        # Add options to the context, checking if they are correct
        if self.options:
            for key in self.options:
                value = self.options[key]
                correct =  key.startswith("*") # * before the letter option indicates the correct answer

                context[f"option{i}"] = value.strip()
                context[f"flag{i}"] = "true" if correct else "false"
                i += 1

        return context

# The QuestionBank class is responsible for reading the question bank files and extracting questions
class QuestionBank:


    def __init__(self, type, path):
        self.type = type # The type of question bank (e.g., 'MCQ', 'String Input')
        self.questions = None # This will hold the list of questions
        self.path = path # The path to the question bank file
        


    def get_questions(self):
      
        with open(self.path, "r") as f:
            file = f.read() 

       

        questions = [] 
    
        # Each question block starts with '###' to indicate a new question 
        pattern = re.compile(r'(###.*?)(?=(?:\n###))', re.DOTALL)
       
        blocks = pattern.findall(file) # Find all sections starting with ###
       
        for block in blocks:
           lines = block.strip().split("\n")
           options = {} # A dictionary to hold options for the question
           dic = {} # A dictionary to hold other question attributes
           for line in lines:
               if not line.strip():
                   continue
               if line != "###" and ": " in line:
                   key, value = line.split(": ", 1)
                   if key.startswith("option") or key.startswith("*"): # options start with option or * for correct answer
                       options[key] = value # # Store MCQ options, '*' marks correct
                   else:
                       dic[key] = value # # Store other attributes like id, question, title, topic, tags, answer

        

            
            

 
        # Create a Question object using the parsed data
           question_obj = Question(
              
               id=dic.get("id"),
               type = dic.get('type'),
               question=dic.get("question"),
               options=options,
               title=dic.get("title"),
               topic=dic.get("topic"),
               tags=dic.get("tags"),
               answer=dic.get("answer", None)
           )

           questions.append(question_obj)

        return questions
# The TemplateManager class is responsible for loading and rendering templates from a file
class TemplateManager:
    def __init__(self, path):
        self.path = path
        self.template_type = self.load_templates() #a dictionary
       
    def load_templates(self):
        with open(self.path, "r") as f:
            file = f.read()

        dic = {}
        sections = re.split(r"###\n", file)  # Split based on '###\n'
        
        for section in sections:
            if section.strip():
                parts = section.split("@", 1)  # Split at the first '@' only
                if len(parts) == 2:
                    type_name = parts[0].strip()
                    template_content = parts[1].strip().replace("###", "")
                    dic[type_name] = template_content
        return dic
    
    # Function to render a template with a given context
    def render_files(self, type, context):
        if type in ['SI', 'DD']:
            html, py = re.split("```", self.template_type.get(type), 1)
            t1 = Template(html)
            t2 = Template(py)
            temp1 = t1.render(context)
            temp2 = t2.render(context)

            return(temp1, temp2)
        else:
            template = Template(self.template_type.get(type))
            return template.render(context)
    
# The QuestionGenerator class is responsible for generating question artifacts and saving them in folders
class QuestionGenerator:
 
    def __init__(self):
       pass


    def generate_question_folder(self,html_content,  info_content, context, py_content=None):
        # Create a folder structure based on topic, type, and title

        title = context["title"].strip().replace(" ", "_")
        topic = context["topic"].strip().replace(" ", "_")
        qtype = context["type"].strip().replace(" ", "_")

        folder_path = os.path.join(topic, qtype, title) # e.g., "Math/MCQ/Question_Title"
        os.makedirs(folder_path, exist_ok=True)
        print(f"Generating files in: {folder_path}")
       

        # Define file paths inside the folder
        html_filename = os.path.join(folder_path, "question.html")
        info_filename = os.path.join(folder_path, "info.json")
        py_filename = os.path.join(folder_path, "server.py") if py_content else None

        with open(html_filename, "w") as f:
            f.write(html_content)

        with open(info_filename, "w") as f:
            f.write(info_content)

        if py_content:
           
            with open(py_filename, "w") as f:
                f.write(py_content)






# Parse command line arguments and generate questions based on the specified mode
parser = argparse.ArgumentParser(description="Generate PrairieLearn questions.")
parser.add_argument("--mode", required=True, choices=["all", "topic", "topic_qtype"], help="Generation mode") # Generate all questions, by topic, or by topic and question type
parser.add_argument("--topic", help="Topic name") # question generation by topic name
parser.add_argument("--qtype", help="Question type (e.g., MCQ, String Input)") # question generation by question type
args = parser.parse_args()

# List of all questions banks (markdown input files) based on their type
question_banks = [
    QuestionBank("String Input", "question_bank.md"),
    QuestionBank("MCQ", "question_bank2.md")
]

# Load the templates and initialize generator
template_manager = TemplateManager("template.md")
generator = QuestionGenerator()

# Main loop: for each question, render and write the PrairieLearn files
for bank in question_banks:
    for question in bank.get_questions():
        qtype = question.type.strip().lower()
        topic = question.topic.strip().lower()

        # Filtering logic
        if args.mode == "topic" and topic != args.topic.strip().lower():
            continue
        elif args.mode == "topic_qtype" and (topic != args.topic.strip().lower() or qtype != args.qtype.strip().lower()):
            continue

        context = question.create_context()

        # Render and write files for MCQs
        if question.type == "MCQ":
            html = template_manager.render_files("MC", context)
            info = template_manager.render_files("IJ", context)
            generator.generate_question_folder(html, info, context)

        # Render and write files for String Input questions
        elif question.type == "String Input":
            html, py = template_manager.render_files("SI", context)
            info = template_manager.render_files("IJ", context)
            generator.generate_question_folder(html, info, context, py_content=py.replace("```", ""))

        # Deal with other question types
        else:
            print(f"Skipping unsupported type: {question.type}")