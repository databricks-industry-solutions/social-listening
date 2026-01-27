import yaml

def get_app_config() -> dict:
    """Get the configuration for the entire application."""
    config_file_path = "config.yaml"
    with open(config_file_path, 'r') as config_file:
        CONFIG_DATA = yaml.safe_load(config_file)
    return CONFIG_DATA

def get_sidebar_config() -> dict:
    """Get the configuration for sidebar links.
    
    Dynamically builds the sidebar configuration from config.yaml.
    Returns a dictionary with sections as keys, each containing display_name and links:
    {"section1": {
        "display_name": "Section 1",
        "links": [
            {"name": "Link 1", "url": "...", "icon": "...", "external": True},
            {"name": "Link 2", "url": "...", "icon": "...", "external": True},
            ...
        ]
    }, ...}
    """
    config_file_path = "config.yaml"
    with open(config_file_path, 'r') as config_file:
        CONFIG_DATA = yaml.safe_load(config_file)

    sidebar_config = CONFIG_DATA['ui']['sidebar']
    link_sections = sidebar_config.get('link_sections', {})
    
    result = {}
    
    # Dynamically build the result dictionary from link_sections
    for section_key, section_data in link_sections.items():
        links_list = []
        
        # Iterate through each link in the section
        for link_key, link_data in section_data.get('links', {}).items():
            link_entry = {
                'name': link_data.get('display_name', link_key.replace('_', ' ').title()),
                'url': link_data.get('url', '#'),
                'icon': link_data.get('icon', ''),
                'external': True  # Default to external links
            }
            links_list.append(link_entry)
        
        # Store the section with its display name and links
        result[section_key] = {
            'display_name': section_data.get('display_name', section_key.replace('_', ' ').title()),
            'links': links_list
        }
    
    return result

def render_sidebar_links(sidebar_config: dict) -> str:
    """Render sidebar links HTML from configuration (e.g. from get_sidebar_config()).
    
    Dynamically renders all sections and links from the config.
    """
    html_parts = []
    
    # Iterate through all sections in the config
    for section_key, section_data in sidebar_config.items():
        display_name = section_data.get('display_name', section_key.replace('_', ' ').title())
        links = section_data.get('links', [])
        
        # Create section container
        section_id = f'{section_key.replace("_", "-")}-section'
        html_parts.append(f'<div class="sidebar-footer-section" id="{section_id}">')
        html_parts.append(f'<h4 class="section-title">{display_name}</h4>')
        
        # Render links in this section
        for link in links:
            target = ' target="_blank"' if link.get('external') else ''
            onclick = f' onclick="event.preventDefault(); alert(\'{link["name"]} - Coming Soon!\');"' if link.get('url') == '#' else ''
            
            # Check if icon is an image path or emoji
            icon = link.get('icon', '')
            if icon.startswith('/') or icon.startswith('http'):
                icon_html = f'<img src="{icon}" alt="{link["name"]}">'
            else:
                icon_html = icon
            
            html_parts.append(f'''
            <a href="{link.get('url', '#')}"{target}{onclick} class="sidebar-link">
                <span class="link-icon">{icon_html}</span>
                <span class="link-text">{link["name"]}</span>
            </a>
        ''')
        
        html_parts.append('</div>')
    
    return '\n'.join(html_parts)