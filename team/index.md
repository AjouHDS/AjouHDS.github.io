---
title: Team
nav:
  order: 1
  tooltip: About Ajou Health Data Science Lab team
---

# {% include icon.html icon="fa-solid fa-users" %}Team

Introducing the team members of the Ajou Health Data Sciences Lab. We strive for both career growth and personal growth in our lab.

{% include section.html %}

## Current members
{% include list.html data="members" component="portrait" filter="role == 'pi'" %} 

{% include list.html data="members" component="portrait" filter="role == 'postdoc'" %}

{% include list.html data="members" component="portrait" filter="role == 'phd'" %}

{% include section.html %}

## Alumni
{% include list.html data="members" component="portrait" filter="role == 'alumni'" %} 

{% include section.html %}

{% capture content %}

{% include figure.html image="images/ajou1.png" %}
{% include figure.html image="images/ajou2.png" %}
{% include figure.html image="images/ajou4.png" %}

{% endcapture %}

{% include grid.html style="square" content=content %}
