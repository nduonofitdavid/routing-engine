# Mini Transport Routing Engine

This repository contains a mini transport engine that makes use of dijkstra or a* algorithm, along with some geometric calculations to find the shortest path between two points.

## Why Build a Mini Transport Routing Engine

During the early stages of my internship in university, I found myself in a relatively new city, where I had no idea of how to get to places. Platforms like google maps provided me with directions on how to get to a destination, but it was not comprehensive in terms of the step by step process of say, enter a car from your current location, to this loction, it was only optimized for drivers say in cars, who could just drive directly to the destination.

The other option was to use services like uber or bolt, but that was not cost efficient, I needed a way to get directions from one place to another, without resulting to asking the locals. 

## How does it work ?

The engine works by using graph traversal algorithms, particularly dijkstra's algorithm, and a* algorithm to find the shortest path between two nodes. Each node is defined as a geographical point on the map, it could be popular junctions where one can find cabs to other junctions, car parks, or metro. A node is defined as:

``` python

{
    "id": int,
    "name": str,
    "latitude": float,
    "longitude": float
}

```

Each node is connected to a set of other nodes through a route, which indicates that one can catch a cab or any transportation service from that node to another node. A route is represented as:

``` python

{
    "id": int,
    "start": int,
    "end": int,
    "time": int,
    "price": int,
    "bi_directional": bool
}

```

A graph is then built using all the nodes provided and their respective routes. This graph can then be explored using dijkstra or a* algorithm to find the path from a particular node to another, effectively providing navigation directions for the user, although not turn by turn navigation, but necessary to explore a new city (depends on the quality of the data provided).

For cases where the user does not want to start their journey from any of the available nodes (i.e junctions, bus stops, parks etc.), the user can enter the latitude and longitude of their starting position, and their destination. 

In order for the algorithm to then find a path from the users starting point to their desired destination, it we first find the nearest node (bus station, park, etc.) to that users starting location, and the nearest node to that users destination.

In order to find the nearest node, we pick the node with the lowest distance. The distance is computed using the **haversine** formula which takes into account the curvature of the earth (it's spherical nature, as supposed to using manhathan distance which operates on a 2D grid.) we then pass the nearest node found for both the starting point and the destination into the algorithm, the algorithm then computes the shortest path. When the path is returned, we loop over the nodes in the path to see if there is any node where the distance between the node and the users destination coordinates is within walking distance (this parameter is set as an environment variable as it may vary across locations.) if we find any, we truncate the path at that node in order to avoid instances where the user is directed back and forth.

A route is then created between the users location, and the starting node in the path, and the ending node in the path and the users destination. In order to compute the time for each their routes, we assumes a base speed of 45km/h for a vehicle, and obtain the time by dividing the distance between them by the optimistic speed. In order to obtain the price, we assume a base price for each hundred meters (this can vary, hence it is an adjustable variable) we then obtain the resulting price by multiplying the base price by the number of 100 meters in the distance. If the price obtained is less than a standard price (this is the standard fare for a trip regardless distance, this can vary, so it is also an editable variable) we use the standard price as the price, else we use the obtained price.

The final path and routes is then passed to the display layer of the application.

An interactive html map is also generated and saved to a specified location, which provides visual explanations about the journey's path, although not as detailed as most platforms like Google Maps, OpenStreetMap etc.

### A* heuristic function

The heuristic function used for the A* algorithm is similar to that used for obtaining the time for an unknown route. It computes the distance between the two nodes, and then converts that distance to a time assuming a base speed of 45km/h

## How to setup the project

More instructions on this soon.