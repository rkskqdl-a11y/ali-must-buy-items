---
layout: default
title: Home
last_updated: "2026-02-02 04:35:26"
---
# Global Hot Deals
*Quality Items & Best Value Picks*

*Last Updated: 2026-02-02 04:35:26 (KST)*

<ul>
  {% for post in site.posts %}
    <li><a href="{{ post.url | relative_url }}">{{ post.date | date: "%Y-%m-%d" }} - {{ post.title }}</a></li>
  {% endfor %}
</ul>