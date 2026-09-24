# confluence-mirror
The Python script for creating a dump of Confluence Space

# What it does
The Python scripts makes a search through a specified Confluence Space and recursively downloads attachments and pages, replacing links to preserve their structure. At the end of each page it saves the tree of the downloaded pages for navigation. Saves pages as simple HTMLs ready to be uploaded to S3 bucket.

# What to do with that
It is not a proper backup to be restored, use the official tools for that. I built it to make a simple mirror of Confluence. This backup is used to uploaded into an S3 bucket and setup a Cloudfront and work as a static web-site with the backup. It doesn't have all cool Atlassian visuals, table of content, etc. Use the tree at the end of each page for navigation or relative links.
