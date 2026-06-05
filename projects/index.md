---
title: Projects
nav:
  order: 3
  tooltip: Ongoing projects, grant information
---

# {% include icon.html icon="fa-solid fa-wrench" %}Projects

## Featured projects

<div class="grid">
{% include list.html component="card" data="projects" filter="group == 'featured'" %}
</div>

{% include section.html %}

## More
{% include search-box.html %}

{% include tags.html tags="epidemiology, ai, informatics" %}

{% include search-info.html %}

{% include list.html component="card" data="projects" style="small" %}
