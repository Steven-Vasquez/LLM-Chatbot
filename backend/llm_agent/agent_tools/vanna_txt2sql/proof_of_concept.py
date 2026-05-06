# Requires vanna_server.py to be running on localhost:8000

import requests
from pprint import pprint

def vanna_text_to_sql(query: str, debug_emit=None) -> str:
    """
    A simple wrapper to call the Vanna server.
    """

    print("Sending the test request to Vanna backend...")

    
    try:
        response = requests.post(
            "http://localhost:8000/custom_agent_query",
            json={"message": query}
        ).json()
    except Exception as e:
        print("Error during request:", e)
        response = None

    #print("Full response:\n")
    #pprint(response)

    start_idx = str(response).rfind("</think>") + 8
    substring = str(response)[start_idx:]
    end_idx = substring.find("\'},")

    if end_idx == -1:
        end_idx = substring.find("\"},")


    final_answer = substring[:end_idx]
    final_answer = final_answer.replace('\\n', '\n')

    print("\nThe final answer is:", final_answer)
    
    return final_answer

    # Print the types of rich content in the chunks for debugging purposes 
    #pprint([c.get("rich", {}).get("type") for c in response["chunks"]])

    import plotly.graph_objects as go

    for chunk in response.get("chunks", []):
        rich = chunk.get("rich")
        if not rich:
            continue

        if rich.get("type") == "chart":
            print("\nVisualization detected. Rendering Plotly figure...\n")

            fig_dict = rich.get("data", {})

            fig = go.Figure(fig_dict)
            
            # Create figure in browser for testing purposes
            fig.show()
            
            # Save the figure as an HTML file
            #fig.write_html("vanna_visualization.html")
            #print("Visualization saved to vanna_visualization.html")
            
            break
                

    ################################################################
    # A debug utility function to summarize the structure of the response
    ################################################################
    '''
    def summarize(obj, depth=0, max_depth=4):
        indent = "  " * depth

        if depth > max_depth:
            return indent + "..."

        if isinstance(obj, dict):
            lines = []
            for k, v in obj.items():
                lines.append(f"{indent}{k}: {type(v).__name__}")
                lines.append(summarize(v, depth + 1, max_depth))
            return "\n".join(lines)

        if isinstance(obj, list):
            lines = [f"{indent}list(len={len(obj)})"]
            if obj:
                lines.append(summarize(obj[0], depth + 1, max_depth))
            return "\n".join(lines)

        return indent + repr(obj)


    for i, chunk in enumerate(response.get("chunks", [])):
        rich = chunk.get("rich")
        if not rich:
            continue

        rtype = rich.get("type")
        if rtype in ("dataframe", "chart"):
            print(f"\n==== CHUNK {i} : {rtype.upper()} STRUCTURE ====\n")
            print(summarize(rich))
    '''
    
test_message = "Show me the distribution of car makes that are compatible with parts that we sell."
#test_message2 = "How many car makes do we sell car parts for?"

#vanna_text_to_sql(test_message)