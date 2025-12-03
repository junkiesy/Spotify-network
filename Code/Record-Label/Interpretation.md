## Record Label Collaboration Network Analysis

### 1. Network Overview

**Network Size**
- Total labels: 117  
- Total label to label ties: 950  
- Average label degree: 16.24  
- Global clustering coefficient: 0.468  
- Largest connected component: 92 labels  
- Total connected components: 7  

**Interpretation**  
The label network is highly interconnected. Nearly all labels belong to one large collaboration cluster.  
The clustering coefficient of approximately 0.47 indicates that when two labels both collaborate with a third label, they are also likely to collaborate with each other, producing many triangle structures.  
The presence of seven total components suggests a few isolated pockets of labels, but the majority belong to the single main component.

---

### 2. Central Labels (Degree Centrality)

**Top Label Hubs**
| Label | Degree |
|-------|--------|
| 300 Entertainment | 85 |
| Alamo | 59 |
| Epic / Freebandz | 58 |
| Columbia | 56 |
| 1017 / Atlantic | 52 |
| Atlantic Records | 51 |
| Cash Money / Young Money / Universal | 51 |
| OVO / Republic | 50 |
| Quality Control (Caroline) | 49 |
| Republic Records | 49 |

**Interpretation**  
300 Entertainment is the dominant hub in the network. It has significantly more connections than any other label.  
This indicates that 300 Entertainment sits at the structural center of the collaboration ecosystem and acts as a major bridge between otherwise separate label clusters.  
Many of the strongest collaboration ties in the dataset involve 300 Entertainment, reinforcing its role as the primary connector in the network.

---

### 3. Strongest Label to Label Collaboration Pairs

**Top Collaboration Pairs**
- 300 Entertainment and 300 Entertainment: 8 collaborations (internal)  
- Alamo and 300 Entertainment: 6  
- 300 Entertainment and Columbia: 5  
- 300 Entertainment and Epic/Freebandz: 5  
- 300 Entertainment and Quality Control (Caroline): 5  
- 300 Entertainment and Republic Records: 5  
- Atlantic Records and 300 Entertainment: 5  

**Interpretation**  
All of the strongest relationships involve 300 Entertainment.  
This demonstrates that 300 Entertainment functions as the primary structural broker between major labels and plays a central role in cross label connectivity.

---

### 4. Interpretation of the High Weight Graph (Edges ≥ 3 Collaborations)

**1. Central Hub**  
300 Entertainment appears as the most influential and connected label. It acts as the core around which the rest of the network is built.

**2. Secondary Hubs**  
Several labels form a ring of secondary importance around the central node. These include:
- Columbia  
- Epic/Freebandz  
- Republic Records  
- Atlantic Records  
- Quality Control Music  
- Motown Records  

These labels form the secondary backbone of collaboration and support the structure of the core.

**3. Outer Peripheral Labels**  
Many labels appear at the edges of the graph with only a single strong connection. Examples include:
- 4PF/CMG  
- GenerationNow/Atlantic  
- South Coast Music Group  
- Cactus Jack / Epic  
- 808 Mafia  

These labels function as leaf nodes. They connect to the core through one strong partnership but do not connect broadly across the network.

**4. Core–Periphery Structure**  
The graph displays a clear core–periphery pattern.  
The core is composed of highly connected labels that collaborate frequently with one another.  
The periphery consists of smaller or more independent labels that rely on the core for access to the wider collaboration ecosystem.  
This structure aligns with real world industry dynamics, where a small number of influential labels control most of the high volume collaboration channels.

---
