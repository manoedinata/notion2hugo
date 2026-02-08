import os
from notion_client import Client
import yaml
from dotenv import load_dotenv
import argparse
import requests
from urllib.parse import urlparse

from notion2hugo import utils
import os

load_dotenv()

notion_token = os.environ.get("NOTION_TOKEN", None)
database_id = os.environ.get("NOTION_DATABASE_ID", None)
if notion_token:
    notion = Client(auth=notion_token)

def download_image(url, save_dir, filename):
    """
    Downloads an image from a URL to the specified directory.
    Returns True if successful.
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    filepath = os.path.join(save_dir, filename)

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        return True

    except Exception as e:
        print(f"Failed to download image {filename}: {e}")
        return False

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
def get_markdown_from_blocks(block_id, image_dir):
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
        elif b_type == "bulleted_list_item" or b_type == "numbered_list_item":
            prefix = "  - "
            text = parse_rich_text(content["rich_text"])
            suffix = "\n"
        elif b_type == "code":
            lang = content["language"]
            code_text = parse_rich_text(content["rich_text"])
            text = f"```{lang}\n{code_text}\n```"

        elif b_type == "image":
            # 1. Get URL (File vs External)
            if content["type"] == "external":
                img_url = content["external"]["url"]
            else:
                img_url = content["file"]["url"]
            
            # 2. Extract Caption
            caption = parse_rich_text(content.get("caption", []))
            
            # 3. Generate Filename (using block ID ensures uniqueness)
            # Parse extension from URL or default to .png
            path = urlparse(img_url).path
            ext = os.path.splitext(path)[1]
            if not ext: ext = ".png"
            
            filename = f"{block['id']}{ext}"
            
            # 4. Download
            download_image(img_url, image_dir, filename)
            
            # 5. Create Markdown Link
            # Syntax: ![Caption](/static/images/slug/id.png)
            text = f"![{caption}]({filename})"

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
def generate_hugo_post(page, output_dir="content/posts", static_dir="static"):
    props = page["properties"]

    # Extract Front Matter
    front_matter = {
        "title": props["Name"]["title"][0]["plain_text"],
        "date": props["Date"]["date"]["start"],
        "draft": props["Draft"]["checkbox"],
        "summary": props["Summary"]["rich_text"][0]["plain_text"] if len(props["Summary"]["rich_text"]) > 0 else "",
        "tags": [f'{t["name"]}' for t in props["Tags"]["multi_select"]]
    }

    # Determine slug
    if len(props["Slug"]["rich_text"]) > 0:
        slug = props["Slug"]["rich_text"][0]["plain_text"]
    else:
        slug = utils.to_dashed(front_matter["title"].lower())

    # Post directories
    post_dir = os.path.join(output_dir, slug)
    if not os.path.exists(post_dir):
        os.makedirs(post_dir)

    # Generate Markdown Content
    body_content = get_markdown_from_blocks(page["id"], post_dir)

    # Combine
    full_post = f"---\n{yaml.dump(front_matter)}---\n\n{body_content}"

    # Save to file
    filepath = os.path.join(post_dir, "index.md")
    with open(filepath, "w") as f:
        f.write(full_post)
    print(f"Generated {filepath}")

def main():
    parser = argparse.ArgumentParser(description="Export Notion Database to Hugo Markdown.")
    parser.add_argument(
        "--output",
        "-o",
        default="content/posts",
        help="Target directory for generated markdown files (default: content/posts)"
    )
    parser.add_argument(
        "--static",
        "-s",
        default="static",
        help="Target directory for static assets like images (default: static)"
    )
    args = parser.parse_args()

    if not notion_token or not database_id:
        raise ValueError("Please set NOTION_TOKEN and NOTION_DATABASE_ID in your environment variables.")

    os.makedirs(args.output, exist_ok=True)

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
        generate_hugo_post(page, output_dir=args.output, static_dir=args.static)
