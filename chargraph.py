import json
import time
import argparse
import os
import requests
from typing import Optional, Dict, Any
from pathlib import Path
import networkx as nx
import matplotlib.pyplot as plt
import google.generativeai as genai

class FileHandler:
    @staticmethod
    def read_file(filename: str) -> str:
        """Read content from a file."""
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    
    @staticmethod
    def read_json(filename: str) -> Optional[Dict[str, Any]]:
        """Read JSON from a file if it exists."""
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    @staticmethod
    def write_json(filename: str, content: Dict[str, Any]) -> None:
        """Write JSON content to a file."""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=4)

class APIClient:
    def __init__(self, api_key: str, use_openrouter: bool = False, model: Optional[str] = None):
        self.api_key = api_key
        self.use_openrouter = use_openrouter
        self.model = model
        self.max_retries = 100
        self.retry_delay = 60  # seconds
    
    def create_messages(self, text: str, previous_json: Optional[Dict[str, Any]] = None, 
                       desc_sentences: Optional[int] = None, generate_portraits: bool = False,
                       copies: int = 1) -> list:
        """Create messages for the API request."""
        system_prompt = """You are a literary analyst specializing in character extraction and relationship mapping. Your task is to:

1. Character Identification:
   - Extract EVERY character mentioned in the text:
     * Include all characters regardless of their role or significance
     * Do not skip minor or briefly mentioned characters
     * If a character is named or described, they must be included
   - Assign unique ID numbers to each character (ensure no duplicates)
   - Determine their common name (most frequently used in text)
   - List ALL references to them (nicknames, titles, etc.)
   - Identify main characters based on:
     * Frequency of appearance
     * Plot significance
     * Number of interactions with others

2. Relationship Analysis:
   - Document ALL character interactions, even brief ones
   - Ensure no duplicate relationships (check both directions: A→B and B→A)
   - For each relationship, provide:
     * Weight (1-10) based on:
       - Frequency of interaction
       - Significance of interactions
       - Impact on plot
     * Positivity scale (-1 to +1):
       - Negative values (-1 to -0.1) for hostile/antagonistic relationships
       - Zero (0) for neutral/professional relationships
       - Positive values (0.1 to 1) for friendly/supportive relationships
       Examples:
       - -1.0: Mortal enemies, intense hatred
       - -0.5: Rivals, strong dislike
       - 0.0: Neutral acquaintances
       - 0.5: Friends, positive relationship
       - 1.0: Best friends, family, deep love
   - Include relationship descriptors (family, friends, enemies, brief encounter, lovers, met in the elevator, etc.)

3. Special Instructions:
   - Include ALL characters, no matter how minor their role
   - Be thorough in relationship mapping
   - Consider indirect interactions
   - Note character development and changing relationships
   - Ensure every character has at least one connection
   - Check for and eliminate any duplicate characters or relationships
   - Never omit a character just because they:
     * Appear only briefly
     * Have few or weak relationships
     * Seem insignificant to the plot
     * Are only mentioned in passing"""

        if desc_sentences is not None:
            system_prompt += f"""

4. Character Descriptions:
   - For each character, provide:
     * A concise description limited to {desc_sentences} sentences
     * Focus on their role, personality traits, and narrative significance
     * Include key story contributions and character development"""

        if generate_portraits:
            system_prompt += """
   
5. Portrait Generation:
   - For each character, create a detailed prompt for AI image generation that captures:
     * Physical appearance and distinguishing features
     * Clothing and style
     * Facial expressions and emotional state
     * Setting or background elements that reflect their role
     * Artistic style suggestions for consistent character representation"""

        if previous_json:
            system_prompt += f"\n\nPreliminary character and relationship data: {json.dumps(previous_json)}\nCarefully update this data: add any missing characters (no matter how minor or briefly mentioned), add missing relationships, verify weights and positivity, ensure all characters have connections, and check for any duplicate characters or relationships. Every character in the text must be included, even those with minimal roles or single appearances."

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text", "text": "\n\n".join([text] * copies)}]}
        ]
    
    def get_schema(self, desc_sentences: Optional[int] = None, generate_portraits: bool = False) -> Dict[str, Any]:
        """Get the JSON schema for the API response."""
        character_properties = {
            "id": {
                "type": "NUMBER",
                "description": "Unique identifier for the character that remains consistent across iterations"
            },
            "common_name": {
                "type": "STRING",
                "description": "The most frequently used name for this character in the text"
            },
            "main_character": {
                "type": "BOOLEAN",
                "description": "True if this is a major character based on frequency of appearance, plot significance, and number of interactions"
            },
            "names": {
                "type": "ARRAY",
                "description": "All variations of the character's name, including nicknames, titles, and other references used in the text",
                "items": {"type": "STRING"}
            }
        }

        if desc_sentences is not None:
            character_properties["description"] = {
                "type": "STRING",
                "description": "Character's role in the story, personality traits, and narrative significance"
            }

        if generate_portraits:
            character_properties["portrait_prompt"] = {
                "type": "STRING",
                "description": "Detailed prompt for AI image generation of the character"
            }

        return {
            "type": "OBJECT",
            "properties": {
                "characters": {
                    "type": "ARRAY",
                    "description": "Characters and connections.",
                    "items": {
                        "type": "OBJECT",
                        "properties": character_properties,
                        "required": ["id", "names", "common_name", "main_character"]
                    }
                },
                "relations": {
                    "type": "ARRAY",
                    "description": "List of each pair of characters who met",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "id1": {
                                "type": "NUMBER",
                                "description": "Unique identifier of the first character in the relationship pair",
                            },
                            "id2": {
                                "type": "NUMBER",
                                "description": "Unique identifier of the second character in the relationship pair",
                            },
                            "relation": {
                                "type": "ARRAY",
                                "description": "Types of relationships between the characters (e.g., family, friends, enemies, colleagues)",
                                "items": {"type": "STRING"}
                            },
                            "weight": {
                                "type": "NUMBER",
                                "description": "Strength of the relationship from 1 (minimal) to 10 (strongest) based on frequency and significance of interactions"
                            },
                            "positivity": {
                                "type": "NUMBER",
                                "description": "Emotional quality of the relationship from -1 (hostile) through 0 (neutral) to 1 (positive)"
                            }
                        },
                        "required": ["id1", "id2", "relation", "weight", "positivity"]
                    }
                },
            },
            "required": ["characters", "relations"]
        }

    def make_request(self, messages: list, desc_sentences: Optional[int] = None, generate_portraits: bool = False, temperature: float = 1) -> dict:
        """Make API request with retry mechanism."""
        if self.use_openrouter:
            # OpenRouter API implementation
            for attempt in range(self.max_retries):
                try:
                    response = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "X-Title": "Character Analyzer"
                        },
                        json={
                            "model": "google/gemini-2.0-flash-exp:free" if self.model is None else self.model,
                            "messages": messages,
                            "temperature": temperature,
                            "response_format": {
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "characters",
                                    "strict": True,
                                    "schema": self.get_schema(desc_sentences, generate_portraits)
                                }
                            }
                        }
                    )
                    
                    if response.status_code == 200 and ("choices" in response.json()):
                        return response.json()
                    
                    print(f"Attempt {attempt + 1} failed. Status: {response.status_code}")
                    print(response.text)
                    
                    if attempt < self.max_retries - 1:
                        print(f"Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
                
                except Exception as e:
                    print(f"Error during attempt {attempt + 1}: {str(e)}")
                    if attempt < self.max_retries - 1:
                        print(f"Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay)
            
            raise Exception("Max retries exceeded")
        else:
            # Gemini implementation
            genai.configure(api_key=self.api_key)
            return_json = genai.protos.FunctionDeclaration(
                name="return_json",
                description="Return json with characters and relationships",
                parameters=self.get_schema(desc_sentences, generate_portraits)
            )
            
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash-exp" if self.model is None else self.model,
                generation_config={"temperature": temperature},
                tools=[return_json]
            )
            
            combined_prompt = f"{messages[0]['content']}\n\nInput text:\n{messages[1]['content'][0]['text']}"
            
            try:
                for attempt in range(self.max_retries):
                    try:
                        result = model.generate_content(combined_prompt, tool_config={'function_calling_config':'ANY'})
                        return result
                        
                    except Exception as e:
                        print(f"Error during attempt {attempt + 1}: {str(e)}")
                        if attempt < self.max_retries - 1:
                            print(f"Retrying in {self.retry_delay} seconds...")
                            time.sleep(self.retry_delay)
                
                raise Exception("Max retries exceeded")
            finally:
                if not hasattr(self, 'use_openrouter') and 'model' in locals():
                    model.close()

class CharacterExtractor:
    def __init__(self, api_key: str, use_openrouter: bool, model: Optional[str] = None):
        self.file_handler = FileHandler()
        self.api_client = APIClient(api_key, use_openrouter, model)
        self.use_openrouter = use_openrouter
    
    def get_output_filename(self, base_filename: str, iteration: int) -> str:
        """Generate output filename with iteration number."""
        path = Path(base_filename)
        return str(path.parent / f"{path.stem}_{iteration}{path.suffix}")
    
    def create_social_network(self, data: Dict[str, Any]) -> nx.Graph:
        """Create a NetworkX graph from character data."""
        G = nx.Graph()
        
        # Add nodes (characters)
        for character in data['characters']:
            G.add_node(
                character['id'],
                common_name=character['common_name'],
                main_character=character['main_character']
            )
        
        # Add edges (relations)
        for relation in data['relations']:
            # If edge exists, append new relations, otherwise create new edge
            if G.has_edge(relation['id1'], relation['id2']):
                G[relation['id1']][relation['id2']]['weight'] += relation['weight']
            else:
                G.add_edge(
                    relation['id1'],
                    relation['id2'],
                    weight=relation['weight']+1,
                    positivity=relation['positivity']
                )
        
        return G

    def plot_network(self, G: nx.Graph, image_file: str) -> None:
        """Plot and save the character network graph."""
        plt.figure(figsize=(15, 15))
        
        # Create layout
        pos = nx.spring_layout(G, k=1, iterations=50)
        
        # Prepare node colors and sizes
        node_colors = []
        node_sizes = []
        for node in G.nodes():
            if G.nodes[node]['main_character']:
                node_colors.append('#FF6B6B')  # Coral red for main characters
                node_sizes.append(2000)
            else:
                node_colors.append('#4ECDC4')  # Turquoise for other characters
                node_sizes.append(1000)
        
        # Draw edges with varying thickness and color based on weight and positivity
        edge_weights = [G[u][v]['weight'] for u, v in G.edges()]
        max_weight = max(edge_weights) if edge_weights else 1
        edge_widths = [20 * (w / max_weight) for w in edge_weights]
        
        edge_colors = []
        for u, v in G.edges():
            positivity = G[u][v]['positivity']
            if positivity < -0.1:
                edge_colors.append('red')
            elif positivity > 0.1:
                edge_colors.append('green')
            else:
                edge_colors.append('grey')
        
        # Draw the network
        nx.draw_networkx_edges(G, pos, alpha=0.2, width=edge_widths, edge_color=edge_colors)
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes)
        
        # Add labels with white background for better visibility
        labels = nx.get_node_attributes(G, 'common_name')
        for node, (x, y) in pos.items():
            plt.text(x, y, labels[node],
                    fontsize=8,
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0.7),
                    horizontalalignment='center',
                    verticalalignment='center')
        
        plt.title("Character Relationship Network", fontsize=16, pad=20)
        plt.axis('off')
        
        # Add legend for nodes
        plt.plot([], [], 'o', color='#FF6B6B', label='Main Characters', markersize=15)
        plt.plot([], [], 'o', color='#4ECDC4', label='Supporting Characters', markersize=15)
        
        # Add legend for edges
        plt.plot([], [], color='red', label='Negative Relations', linewidth=3)
        plt.plot([], [], color='grey', label='Neutral Relations', linewidth=3)
        plt.plot([], [], color='green', label='Positive Relations', linewidth=3)
        
        plt.legend(fontsize=12, loc='upper left', bbox_to_anchor=(1, 1))
        
        plt.tight_layout()
        plt.savefig(image_file, dpi=300, bbox_inches='tight')
        plt.close()

    def process_text(self, input_file: str, output_file: str, previous_json_file: Optional[str] = None,
                    iterations: int = 1, delay: int = 300, plot_graph: bool = False,
                    desc_sentences: Optional[int] = None, generate_portraits: bool = False,
                    copies: int = 1, temperature: float = 1.0) -> None:
        """Process text file and extract character information."""
        text = self.file_handler.read_file(input_file)
        previous_json = None
        
        for i in range(iterations):
            if i > 0:
                # Use previous iteration's output as input
                previous_json = self.file_handler.read_json(
                    self.get_output_filename(output_file, i - 1)
                )
                # Wait between iterations
                print(f"Waiting {delay} seconds before next iteration...")
                time.sleep(delay)
            elif previous_json_file:
                previous_json = self.file_handler.read_json(previous_json_file)
            
            print(f"Starting iteration {i + 1}/{iterations}")
            
            # Add retry mechanism for the entire API request and JSON parsing process
            max_retries = 10
            retry_delay = 10
            for attempt in range(max_retries):
                try:
                    messages = self.api_client.create_messages(text, previous_json, desc_sentences, generate_portraits, copies)
                    result = self.api_client.make_request(messages, desc_sentences, generate_portraits, temperature)
                    
                    output_filename = self.get_output_filename(output_file, i)
                                        
                    # Log response content for debugging
                    debug_filename = str(Path(output_filename).with_suffix('.debug.txt'))
                    with open(debug_filename, 'w', encoding='utf-8') as f:
                        f.write(f"Attempt {attempt + 1} Result Content:\n{result}")

                    if self.use_openrouter:
                        content = json.loads(result["choices"][0]["message"]["content"])
                    else:
                        fc = result.candidates[0].content.parts[0].function_call
                        content = type(fc).to_dict(fc)["args"]
                    
                    # Try to parse and validate the JSON structure
                    #content = json.loads(response_content)
                    
                    # Basic validation of required fields
                    if not isinstance(content, dict):
                        raise ValueError("Response content is not a JSON object")
                    if "characters" not in content or "relations" not in content:
                        raise ValueError("Missing required top-level fields")
                    if not isinstance(content["characters"], list) or not isinstance(content["relations"], list):
                        raise ValueError("characters and relations must be arrays")
                    
                    # Save the validated content
                    self.file_handler.write_json(output_filename, content)
                    print(f"Results saved to {output_filename}")
                    
                    if plot_graph:
                        # Set random seed for consistent layouts
                        import random
                        random.seed(42)
                        
                        # Create and save graph
                        image_filename = str(Path(output_filename).with_suffix('.png'))
                        G = self.create_social_network(content)
                        self.plot_network(G, image_filename)
                        print(f"Graph saved to {image_filename}")
                    
                    # If we get here, the iteration was successful
                    break
                    
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    print(f"Error on attempt {attempt + 1}: {str(e)}")
                    if attempt < max_retries - 1:
                        print(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        raise Exception(f"Failed to process iteration {i + 1} after {max_retries} attempts")

def cleanup_genai():
    """Clean up Gemini API resources."""
    try:
        genai.reset()
    except:
        pass

def main():
    parser = argparse.ArgumentParser(description='Extract characters and their relationships from text.')
    parser.add_argument('input_file', help='Input text file to analyze')
    parser.add_argument('output_file', help='Base name for output JSON files')
    parser.add_argument('-iter', '--iterations', type=int, default=1,
                      help='Number of iterations to run (default: 1)')
    parser.add_argument('-delay', '--delay', type=int, default=10,
                      help='Delay between iterations in seconds (default: 10)')
    parser.add_argument('-prev', '--previous', 
                      help='Previous JSON file to use as initial data')
    parser.add_argument('-plot', '--plot_graph', action='store_true',
                      help='Generate character relationship graph for each iteration')
    parser.add_argument('-desc', '--desc_sentences', type=int,
                      help='Number of sentences to use for character descriptions')
    parser.add_argument('-portrait', '--generate_portraits', action='store_true',
                      help='Generate AI portrait prompts for each character')
    parser.add_argument('-cp', '--copies', type=int, default=1,
                      help='Number of copies of text to send as prompt (default: 1)')
    parser.add_argument('-t', '--temperature', type=float, default=1.0,
                      help='Temperature (default: 1.0)')
    parser.add_argument('-or', '--openrouter', action='store_true',
                      help='Use OpenRouter API instead of Gemini')
    parser.add_argument('-m', '--model', type=str, default=None,
                      help='Model to use (default: gemini-2.0-flash-exp for Gemini, google/gemini-2.0-flash-exp:free for OpenRouter)')
    
    args = parser.parse_args()
    
    if args.openrouter:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required when using --openrouter")
    else:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    extractor = CharacterExtractor(api_key, args.openrouter, args.model)
    extractor.process_text(
        input_file=args.input_file,
        output_file=args.output_file,
        previous_json_file=args.previous,
        iterations=args.iterations,
        delay=args.delay,
        plot_graph=args.plot_graph,
        desc_sentences=args.desc_sentences,
        generate_portraits=args.generate_portraits,
        copies=args.copies,
        temperature=args.temperature
    )

if __name__ == "__main__":
        main()
