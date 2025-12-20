---
title: Team
nav:
  order: 3
  tooltip: About Ajou Health Data Science Lab team
---

# {% include icon.html icon="fa-solid fa-users" %}Team

Introducing the team members of the Ajou Health Data Sciences Lab. We strive for both career growth and personal growth in our lab.

{% include section.html %}

{% include list.html data="members" component="portrait" filter="role == 'pi'" %}
{% include list.html data="members" component="portrait" filter="role != 'pi'" %}

{% include section.html background="images/background.jpg" dark=true %}

We are actively recruiting new members! If you are interested, please send your CV to us via email.

{% include section.html %}

{% capture content %}

{% include figure.html image="images/ajou1.png" %}
{% include figure.html image="images/ajou2.png" %}
{% include figure.html image="images/ajou3.png" %}

{% endcapture %}

{% include grid.html style="square" content=content %}
