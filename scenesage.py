#!/usr/bin/env python3

import os
import json
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta

import pysrt
import typer
from rich.console import Console
from rich.progress import Progress
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain_google_genai import ChatGoogleGenerativeAI
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()

# Debug: Print if API keys are loaded (first few characters only)
google_api_key = os.getenv("GOOGLE_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

if google_api_key:
    print(f"Google API Key loaded: {google_api_key[:8]}...")
else:
    print("Warning: GOOGLE_API_KEY not found in environment variables")

if openai_api_key:
    print(f"OpenAI API Key loaded: {openai_api_key[:8]}...")
else:
    print("Warning: OPENAI_API_KEY not found in environment variables")

if not google_api_key and not openai_api_key:
    raise ValueError("At least one of GOOGLE_API_KEY or OPENAI_API_KEY must be present in environment variables")

# Initialize Typer app and console
app = typer.Typer()
console = Console()

def parse_time(time_str: str) -> datetime:
    """Convert SRT time string to datetime object."""
    return datetime.strptime(time_str, "%H:%M:%S,%f")

def format_time(dt: datetime) -> str:
    """Convert datetime to SRT time string."""
    return dt.strftime("%H:%M:%S,%f")[:-3]

def format_subrip_time(time: pysrt.SubRipTime) -> str:
    """Convert SubRipTime to string format."""
    return f"{time.hours:02d}:{time.minutes:02d}:{time.seconds:02d},{time.milliseconds:03d}"

def detect_scenes(subtitles: pysrt.SubRipFile, min_pause: int = 4) -> List[dict]:
    """Split subtitles into scenes based on pauses."""
    scenes = []
    current_scene = {
        "start": subtitles[0].start,
        "end": subtitles[0].end,
        "text": subtitles[0].text
    }
    
    for i in range(1, len(subtitles)):
        current = subtitles[i]
        prev = subtitles[i-1]
        
        # Calculate pause duration in seconds
        pause = (parse_time(format_subrip_time(current.start)) - 
                parse_time(format_subrip_time(prev.end))).total_seconds()
        
        if pause >= min_pause:
            # End of scene
            scenes.append(current_scene)
            current_scene = {
                "start": current.start,
                "end": current.end,
                "text": current.text
            }
        else:
            # Continue current scene
            current_scene["end"] = current.end
            current_scene["text"] += " " + current.text
    
    # Add the last scene
    scenes.append(current_scene)
    return scenes

def get_llm(model_name: str, temperature: float = 0.7, max_tokens: int = 1000, 
            top_p: float = 0.95, frequency_penalty: float = 0.0, 
            presence_penalty: float = 0.0):
    """Initialize the appropriate LLM based on model name."""
    if model_name.startswith("gemini"):
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=temperature,
            max_output_tokens=max_tokens,
            top_p=top_p,
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
    else:
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty
        )

async def analyze_scene_async(scene: dict, llm) -> Dict:
    """Asynchronous version of analyze_scene."""
    try:
        # Define response schemas for structured output
        response_schemas = [
            ResponseSchema(name="summary", description="A one-sentence summary of the scene"),
            ResponseSchema(name="characters", description="List of characters mentioned in the scene (comma-separated)"),
            ResponseSchema(name="mood", description="The mood or emotion of the scene"),
            ResponseSchema(name="cultural_refs", description="List of up to 3 cultural references (comma-separated)")
        ]
        
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
        format_instructions = output_parser.get_format_instructions()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a film analysis expert. Analyze the following movie scene and provide:
            1. A one-sentence summary
            2. Characters mentioned (as a comma-separated list)
            3. The mood/emotion
            4. Up to 3 cultural references (as a comma-separated list)
            
            {format_instructions}"""),
            ("user", f"""Scene transcript:
            {scene['text']}
            
            Start time: {format_subrip_time(scene['start'])}
            End time: {format_subrip_time(scene['end'])}""")
        ])
        
        chain = prompt | llm | output_parser
        
        # Run the chain in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool,
                lambda: chain.invoke({"format_instructions": format_instructions})
            )
        
        # Post-process the results
        if isinstance(result['characters'], str):
            result['characters'] = [char.strip() for char in result['characters'].split(',') if char.strip()]
        if isinstance(result['cultural_refs'], str):
            result['cultural_refs'] = [ref.strip() for ref in result['cultural_refs'].split(',') if ref.strip()]
        
        # Add scene metadata
        result.update({
            "start": format_subrip_time(scene["start"]),
            "end": format_subrip_time(scene["end"]),
            "transcript": scene["text"]
        })
        
        return result
    except Exception as e:
        console.print(f"[bold red]Error in analyze_scene_async: {str(e)}[/]")
        console.print(f"[bold red]Error type: {type(e)}[/]")
        raise Exception(f"Failed to analyze scene: {str(e)}")

async def process_chunk(chunk: List[dict], context: str, llm) -> List[Dict]:
    """Process a single chunk of scenes asynchronously."""
    tasks = []
    for scene in chunk:
        # Keep the original scene text without adding context
        tasks.append(analyze_scene_async(scene, llm))
    return await asyncio.gather(*tasks)

async def process_scene_chunks_async(scenes: List[dict], llm, chunk_size: int = 5, overlap: int = 2) -> List[dict]:
    """Process scenes in chunks with overlap to maintain context, using async processing."""
    analyzed_scenes = []
    total_scenes = len(scenes)
    
    for i in range(0, total_scenes, chunk_size - overlap):
        # Get chunk of scenes with overlap
        chunk_end = min(i + chunk_size, total_scenes)
        chunk = scenes[i:chunk_end]
        
        # Process the chunk asynchronously
        chunk_results = await process_chunk(chunk, "", llm)
        analyzed_scenes.extend(chunk_results)
    
    return analyzed_scenes

def process_scene_chunks(scenes: List[dict], llm, chunk_size: int = 5, overlap: int = 2) -> List[dict]:
    """Synchronous wrapper for process_scene_chunks_async."""
    return asyncio.run(process_scene_chunks_async(scenes, llm, chunk_size, overlap))

def analyze_scene(scene: dict, llm) -> Dict:
    """Synchronous wrapper for analyze_scene_async."""
    return asyncio.run(analyze_scene_async(scene, llm))

@app.command()
def main(
    input_file: str = typer.Argument(..., help="Input SRT file"),
    output_file: str = typer.Option("scenes.json", help="Output JSON file"),
    model: str = typer.Option("gpt-3.5-turbo", help="LLM model to use (e.g., gpt-3.5-turbo, gemini-pro)"),
    min_pause: int = typer.Option(4, help="Minimum pause duration in seconds to split scenes"),
    chunk_size: int = typer.Option(5, help="Number of scenes to process in each chunk"),
    overlap: int = typer.Option(2, help="Number of scenes to overlap between chunks")
):
    """Analyze movie scenes from subtitle file using LLM."""
    try:
        # Load subtitles
        subtitles = pysrt.open(input_file)
        
        # Initialize LLM
        llm = get_llm(model)
        
        # Detect scenes
        console.print("[bold blue]Detecting scenes...[/]")
        scenes = detect_scenes(subtitles, min_pause)
        
        # Analyze scenes in chunks
        console.print("[bold blue]Analyzing scenes...[/]")
        analyzed_scenes = process_scene_chunks(scenes, llm, chunk_size, overlap)
        
        # Save results
        with open(output_file, 'w') as f:
            json.dump(analyzed_scenes, f, indent=2)
        
        console.print(f"[bold green]Analysis complete! Results saved to {output_file}[/]")
        
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/]")
        console.print(f"[bold red]Error type: {type(e)}[/]")
        raise typer.Exit(1)

if __name__ == "__main__":
    app() 