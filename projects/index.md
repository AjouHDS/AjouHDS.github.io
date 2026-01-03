---
title: Projects
nav:
  order: 3
  tooltip: Ongoing projects, grant information
---

# {% include icon.html icon="fa-solid fa-wrench" %}Projects

## Featured projects

{% include list.html component="card" data="projects" filter="group == 'featured'" %}

{% include section.html %}

## More
{% include search-box.html %}

{% include tags.html tags="project, grant, EHR, Claims, collaborative, OHDSI, resource, website" %}

{% include search-info.html %}

{% include list.html component="card" data="projects" filter="!group" style="small" %}
