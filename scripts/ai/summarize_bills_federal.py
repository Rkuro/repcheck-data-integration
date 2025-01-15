from sqlalchemy.sql import select
import requests
import logging
import traceback
import os
import tempfile
from pdfminer.high_level import extract_text
from openai import OpenAI
import re
import tiktoken


from ..database.models import Bill
from ..database.database import get_session
from ..logging_config import setup_logging

log = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.getcwd(), "_data", "ai", "bills_summary_federal")

openai_client = OpenAI()

def num_tokens_from_messages(messages, model="gpt-4o"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using o200k_base encoding.")
        encoding = tiktoken.get_encoding("o200k_base")
    if model in {
        "gpt-3.5-turbo-0125",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        "gpt-4o-mini-2024-07-18",
        "gpt-4o-2024-08-06"
        }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif "gpt-3.5-turbo" in model:
        print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0125.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0125")
    elif "gpt-4o-mini" in model:
        print("Warning: gpt-4o-mini may update over time. Returning num tokens assuming gpt-4o-mini-2024-07-18.")
        return num_tokens_from_messages(messages, model="gpt-4o-mini-2024-07-18")
    elif "gpt-4o" in model:
        print("Warning: gpt-4o and gpt-4o-mini may update over time. Returning num tokens assuming gpt-4o-2024-08-06.")
        return num_tokens_from_messages(messages, model="gpt-4o-2024-08-06")
    elif "gpt-4" in model:
        print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens

def clean_pdf_text(text):
    # Remove form feed and weird characters
    text = re.sub(r'\x0c', '', text)

    # Remove newline chars
    text = re.sub(r'\n', '', text)

    # Remove standalone numbers (e.g., line numbers)
    # text = re.sub(r'^\d+\s*', '', text, flags=re.MULTILINE)

    # Collapse unnecessary line breaks
    # text = re.sub(r'\n(?!\n)', ' ', text)

    text = text.encode('ascii', 'ignore').decode()

    return text

def send_summary_api_call(content):

    messages = [
        {"role": "developer", "content": "You summarize legislation for citizens. Make your outputs understandable to the everyday person."},

    ]

    # user_content = (
    # f"""
    # Please summarize the following legislation text. Please only reference the content provided for your summary.
    #
    # Your output should look like the following:
    #
    # $ Title
    # $ Executive Summary
    # -----------------------------------------------------------
    # $ Bullet points of specific information from the legislation
    #
    #
    # Legislation content:
    # {content}
    # """
    # )

    user_content = "Test legislation"

    messages.append(
        {"role": "user", "content": user_content}
    )

    log.info(num_tokens_from_messages(messages))

    # completion = openai_client.chat.completions.create(
    #     model="gpt-4o",
    #     messages=messages,
    #     # stream = True
    # )

    # log.info(completion)

    # for chunk in completion:
    #     log.info(chunk)

def summarize_pdf(pdf_url):

    try:
        response = requests.get(pdf_url)

        # Write to tempfile
        with tempfile.NamedTemporaryFile(dir=DATA_DIR) as f:
            f.write(response.content)

            pdf_filepath = f.name

            pdf_string_content_full = extract_text(pdf_filepath)

            text_cleaned = clean_pdf_text(pdf_string_content_full)

            log.info(repr(pdf_string_content_full))
            log.info(repr(text_cleaned))
            response = send_summary_api_call(text_cleaned)



    except Exception as e:
        log.exception(e)
        log.error(traceback.format_exc())

def main():

    # Setup
    os.makedirs(DATA_DIR, exist_ok=True)
    with get_session() as session:

        summarize_pdf("https://www.govinfo.gov/content/pkg/BILLS-119hr29eh/pdf/BILLS-119hr29eh.pdf")
        # # Fetch federal bills
        # bills = session.exec(
        #     select(
        #
        #     )
        # )


if __name__ == "__main__":
    setup_logging()
    main()