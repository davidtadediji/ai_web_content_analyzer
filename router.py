# router.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

from pydantic import BaseModel, HttpUrl
from logger import configured_logger
from main import SummaryGenerator, SummaryOutputStrategy, openai, MODEL, get_summary_user_prompt
from dotenv import load_dotenv

from prompt import system_prompt_for_summary

load_dotenv()
import os

app_name = os.getenv("APP_NAME")
router = APIRouter(
    prefix="/api",
    tags=[app_name],
    responses={404: {"description": "Not found"}},
)


# Define the expected JSON body schema
class Request(BaseModel):
    company_name: str
    url: HttpUrl  # The key in the JSON body containing the website url


class APIStreamingOutputStrategy(SummaryOutputStrategy):
    async def handle_output(self, messages):
        """
        Streams output directly to the FastAPI client as it is being generated.

        Args:
            messages (list): The messages to send to OpenAI.

        Returns:
            StreamingResponse: A FastAPI StreamingResponse object.
        """
        try:
            # Initialize the OpenAI API stream
            response = openai.chat.completions.create(
                model=MODEL,
                messages=messages,
                stream=True,
            )

            async def stream_generator():
                for chunk in response:
                    # More precise way to extract content from delta
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        yield content

            # Return the stream generator as a FastAPI StreamingResponse
            return StreamingResponse(stream_generator(), media_type="text/plain")

        except Exception as e:
            # Log and raise a detailed error
            error_message = f"Error in APIStreamingOutputStrategy --> {str(e)}"
            configured_logger.error(error_message, exc_info=True)
            raise RuntimeError(error_message)

@router.post("/analyze/")
async def generate_summary(request: Request):
    """
    Generate a summary for the given website URL and stream the result.
    Args:
        request (Request): JSON object with an "url" key.
    Returns:
        StreamingResponse: Streamed summary result.
    """
    try:
        website_url = request.url

        # Log the received URL
        configured_logger.info("Received Website URL: %s", website_url)

        # Create the appropriate output strategy for streaming
        strategy = APIStreamingOutputStrategy()


        # Prepare the messages for the OpenAI API
        messages = [
            {"role": "system", "content": system_prompt_for_summary},
            {"role": "user", "content": get_summary_user_prompt(request.company_name, website_url)},
        ]


        # Use the strategy to generate the streamed response
        return await strategy.handle_output(messages)

    except Exception as e:
        # Handle errors gracefully
        configured_logger.error(f"Error generating summary --> {str(e)}")
        return JSONResponse(
            content={"error": f"Failed to generate summary: {str(e)}"},
            status_code=500,
        )
