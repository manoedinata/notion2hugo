import os
from notion_client import Client
import yaml
from dotenv import load_dotenv

from notion2hugo import utils
import os

load_dotenv()
notion_token = os.environ["NOTION_TOKEN"]
database_id = os.environ["NOTION_DATABASE_ID"]

notion = Client(auth=notion_token)

# 1. Helper to parse Rich Text arrays
def parse_rich_text(rich_text_list):
    text_content = ""
    for text in rich_text_list:
        plain = text["plain_text"]
        # Add logic here for annotations (bold, italic, code, link)
        if text["annotations"]["bold"]:
            plain = f"**{plain}**"
        if text["annotations"]["code"]:
            plain = f"`{plain}`"
        if text["href"]:
            plain = f"[{plain}]({text['href']})"
        text_content += plain
    return text_content

# 2. Recursive function to fetch blocks and children
def get_markdown_from_blocks(block_id):
    markdown_output = ""

    # Handle pagination (cursor) if needed, simplified here
    blocks = notion.blocks.children.list(block_id=block_id)["results"]

    for block in blocks:
        b_type = block["type"]
        content = block[b_type] # Get the specific block data
        
        prefix = ""
        suffix = "\n\n"
        text = ""

        # Switch-case for block types
        if b_type == "paragraph":
            text = parse_rich_text(content["rich_text"])
        elif b_type == "heading_1":
            prefix = "# "
            text = parse_rich_text(content["rich_text"])
        elif b_type == "heading_2":
            prefix = "## "
            text = parse_rich_text(content["rich_text"])
        elif b_type == "bulleted_list_item":
            prefix = "  - "
            text = parse_rich_text(content["rich_text"])
            suffix = "\n"
        elif b_type == "code":
            lang = content["language"]
            code_text = parse_rich_text(content["rich_text"])
            text = f"```{lang}\n{code_text}\n```"
        
        # --- RECURSION FOR NESTED BLOCKS ---
        if block["has_children"]:
            # Recurse using this block's ID as the new parent
            children_md = get_markdown_from_blocks(block["id"])
            # Indent children (simple approach)
            indented_children = "\n".join(["    " + line for line in children_md.split("\n")])
            text += "\n" + indented_children

        markdown_output += f"{prefix}{text}{suffix}"

    markdown_output = markdown_output.strip()
    return markdown_output

# 3. Main function to build the page
def generate_hugo_post(page):
    props = page["properties"]
    
    # Extract Front Matter
    front_matter = {
        "title": props["Name"]["title"][0]["plain_text"],
        "date": props["Date"]["date"]["start"],
        "draft": props["Draft"]["checkbox"],
        "tags": [f'{t["name"]}' for t in props["Tags"]["multi_select"]]
    }

    # Generate Markdown Content
    body_content = get_markdown_from_blocks(page["id"])
    
    # Combine
    full_post = f"---\n{yaml.dump(front_matter)}---\n\n{body_content}"

    # Determine slug
    if len(props["Slug"]["rich_text"]) > 0:
        slug = props["Slug"]["rich_text"][0]["plain_text"]
    else:
        slug = utils.to_dashed(front_matter["title"].lower())

    # Save to file
    with open(f"content/posts/{slug}.md", "w") as f:
        f.write(full_post)
    print(f"Generated {slug}.md")

def main():
    os.makedirs("content/posts", exist_ok=True)

    print("Retrieving the correct data source ID...")
    data_source_id = next(
        (item["id"] for item in notion.databases.retrieve(database_id=database_id)["data_sources"] if item["name"] == "Posts"),
        None
    )
    if not data_source_id:
        raise ValueError("Data source 'Posts' not found in the database.")

    print("Querying the database...")
    query = notion.data_sources.query(
        database_id=database_id,
        data_source_id=data_source_id
    )

    for page in query["results"]:
        generate_hugo_post(page)
