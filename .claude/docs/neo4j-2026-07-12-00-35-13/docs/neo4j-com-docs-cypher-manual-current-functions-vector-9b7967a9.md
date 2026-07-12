---
title: "Vector functions"
source_url: "https://neo4j.com/docs/cypher-manual/current/functions/vector/"
host: "neo4j.com"
depth: 1
selector: "article,main,[role=main]"
fetched_at: "2026-07-12T00:35:12.725Z"
---
[](https://neo4j.com/docs)

[Raise an issue](https://github.com/neo4j/docs-cypher/issues/new/?title=Docs%20Feedback%20modules/ROOT/pages/functions/vector.adoc%20\(ref:%20cypher-25\)&body=%3E%20Do%20not%20include%20confidential%20information,%20personal%20data,%20sensitive%20data,%20or%20other%20regulated%20data.)

# Vector functions

Vector functions allow you to construct [`VECTOR` values](https://neo4j.com/docs/cypher-manual/current/values-and-types/vector/), compute the similarity and distance of vector pairs, and calculate the size of a vector.

## [](https://neo4j.com/docs/cypher-manual/current/functions/vector/#functions-vector)vector()

Cypher 25 onlyIntroduced in Neo4j 2025.10

<table class="tableblock frame-all grid-all stretch"><caption class="title">Details</caption> <colgroup><col style="width: 25%;"> <col style="width: 25%;"> <col style="width: 25%;"> <col style="width: 25%;"></colgroup><tbody><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Syntax</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock"><code>vector(vectorValue, dimension, coordinateType)</code></p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Description</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock">Constructs a <a href="https://neo4j.com/docs/cypher-manual/current/values-and-types/vector/" class="xref page"><code>VECTOR</code></a> value.</p></td></tr><tr><td class="tableblock halign-left valign-top" rowspan="4"><p class="tableblock"><strong>Arguments</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Name</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Type</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Description</strong></p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vectorValue</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>STRING</code> | <code>LIST&lt;INTEGER | FLOAT&gt;</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">The numeric values to create the vector coordinates from.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>dimension</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>INTEGER</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">The dimension (number of coordinates) of the vector.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>coordinateType</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>[INTEGER64, INTEGER32, INTEGER16, INTEGER8, FLOAT64, FLOAT32]</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">The type of each coordinate in the vector.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Returns</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock"><a href="https://neo4j.com/docs/cypher-manual/current/values-and-types/vector/" class="xref page"><code>VECTOR</code></a></p></td></tr></tbody></table>

<table class="tableblock frame-all grid-all stretch"><caption class="title">Considerations</caption> <colgroup><col style="width: 100%;"></colgroup><tbody><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>VECTOR</code> values can be <a href="https://neo4j.com/docs/cypher-manual/current/values-and-types/vector/#store-vector-properties" class="xref page">stored as properties</a>.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">If a <code>STRING</code> is used in <code>vectorValue</code>, it must start and end with square brackets (<code>[]</code>). The values inside the brackets must be comma-separated numbers, represented in either decimal or scientific notation.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>null</code>, <code>NaN</code>, and <code>Infinity</code> values are not allowed as coordinate values.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">If <code>vectorValue</code> contains elements that are not of the specified <code>coordinateType</code>, they will be coerced to that coordinate type if possible. This includes the potential of lossy conversion in cases where a larger type, e.g. <code>INTEGER64</code> does not fit into the specified type, e.g. <code>FLOAT32</code>.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>dimension</code> must be greater than <code>0</code> and less than or equal to <code>4096</code>.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">A <code>null</code> <code>vectorValue</code> or <code>dimension</code> will return <code>null</code>.</p></td></tr></tbody></table>

Example 1. Construct a `VECTOR` value

Query

```cypher
RETURN vector([1, 2, 3], 3, INTEGER) AS vector
```

Result
| vector |
| --- |
|
`vector([1, 2, 3], 3, INTEGER NOT NULL)`

 |
|

Rows: 1

 |

Example 2. Construct a `VECTOR` value with a `STRING` as `vectorValue`

Query

```cypher
RETURN vector("[1.05000e+00, 0.123, 5]", 3, FLOAT) AS vector
```

Result
| vector |
| --- |
|
`vector([1.05, 0.123, 5.0], 3, FLOAT NOT NULL)`

 |
|

Rows: 1

 |

Example 3. `null` values

Query

```cypher
RETURN vector(null, 3, FLOAT32) AS nullVectorValue,
       vector([1, 2, 3], null, INTEGER8) AS nullDimension
```

Result
| nullVectorValue | nullDimension |
| --- | --- |
|
`null`

 |

`null`

 |
|

Rows: 1

 |

## [](https://neo4j.com/docs/cypher-manual/current/functions/vector/#functions-similarity-cosine)vector.similarity.cosine()

<table class="tableblock frame-all grid-all stretch"><caption class="title">Details</caption> <colgroup><col style="width: 25%;"> <col style="width: 25%;"> <col style="width: 25%;"> <col style="width: 25%;"></colgroup><tbody><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Syntax</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock"><code>vector.similarity.cosine(a, b)</code></p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Description</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock">Returns a <code>FLOAT</code> representing the similarity between the argument vectors based on their cosine.</p></td></tr><tr><td class="tableblock halign-left valign-top" rowspan="3"><p class="tableblock"><strong>Arguments</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Name</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Type</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Description</strong></p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>a</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>VECTOR</code> | <code>LIST&lt;INTEGER | FLOAT&gt;</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">A vector or list value representing the first vector.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>b</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>VECTOR</code> | <code>LIST&lt;INTEGER | FLOAT&gt;</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">A vector or list value representing the second vector.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Returns</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock"><code>FLOAT</code></p></td></tr></tbody></table>

<table class="tableblock frame-all grid-all stretch"><caption class="title">Considerations</caption> <colgroup><col style="width: 100%;"></colgroup><tbody><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vector.similarity.cosine(null, null)</code> returns <code>null</code>.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vector.similarity.cosine(null, b)</code> returns <code>null</code>.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vector.similarity.cosine(a, null)</code> returns <code>null</code>.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">Both vectors must be of the same dimension.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">Both vectors must be <a href="https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/#similarity-functions" class="xref page"><strong>valid</strong></a> with respect to cosine similarity.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">The implementation is the same of the latest vector index provider (<code>vector-2.0</code>).</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">The similarity score ranges from <code>0</code> and <code>1</code>, with scores closer to <code>1</code> indicating a higher degree of similarity.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">The input arguments <code>a</code> and <code>b</code> accept <code>VECTOR</code> values as of Neo4j 2025.10.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">Floating point operations are performed with <code>float32</code> arithmetic.</p></td></tr></tbody></table>

For more details, see the [vector index documentation](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/#similarity-functions).

## [](https://neo4j.com/docs/cypher-manual/current/functions/vector/#functions-similarity-euclidean)vector.similarity.euclidean()

<table class="tableblock frame-all grid-all stretch"><caption class="title">Details</caption> <colgroup><col style="width: 25%;"> <col style="width: 25%;"> <col style="width: 25%;"> <col style="width: 25%;"></colgroup><tbody><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Syntax</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock"><code>vector.similarity.euclidean(a, b)</code></p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Description</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock">Returns a <code>FLOAT</code> representing the similarity between the argument vectors based on their Euclidean distance.</p></td></tr><tr><td class="tableblock halign-left valign-top" rowspan="3"><p class="tableblock"><strong>Arguments</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Name</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Type</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Description</strong></p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>a</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>VECTOR</code> | <code>LIST&lt;INTEGER | FLOAT&gt;</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">A vector or list value representing the first vector.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>b</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>VECTOR</code> | <code>LIST&lt;INTEGER | FLOAT&gt;</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">A vector or list value representing the second vector.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Returns</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock"><code>FLOAT</code></p></td></tr></tbody></table>

<table class="tableblock frame-all grid-all stretch"><caption class="title">Considerations</caption> <colgroup><col style="width: 100%;"></colgroup><tbody><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vector.similarity.euclidean(null, null)</code> returns <code>null</code>.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vector.similarity.euclidean(null, b)</code> returns <code>null</code>.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vector.similarity.euclidean(a, null)</code> returns <code>null</code>.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">Both vectors must be of the same dimension.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">Both vectors must be <a href="https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/#similarity-functions" class="xref page"><strong>valid</strong></a> with respect to Euclidean similarity.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">The implementation is the same of the latest available vector index provider (<code>vector-2.0</code>).</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">The similarity score ranges from <code>0</code> and <code>1</code>, with scores closer to <code>1</code> indicating a higher degree of similarity.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">The input arguments <code>a</code> and <code>b</code> accept <code>VECTOR</code> values as of Neo4j 2025.10.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">Floating point operations are performed with <code>float32</code> arithmetic.</p></td></tr></tbody></table>

For more details, see the [vector index documentation](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/#similarity-functions).

Example 4. k-Nearest Neighbors

*k*\-nearest neighbor queries return the *k* entities with the highest similarity scores based on comparing their associated vectors with a query vector. Such queries can be run against vector indexes in the form of *approximate* *k*\-nearest neighbor (k-ANN) queries, whose returned entities have a high probability of being among the true *k* nearest neighbors. However, they can also be expressed as an exhaustive search using vector similarity functions directly. While this is typically significantly slower than using an index, it is exact rather than approximate and does not require an existing index. This can be useful for one-off queries on small datasets.

To create the graph used in this example, run the following query on an empty Neo4j database:

```cypher
CREATE
  (:Node { id: 1, vector: vector([1.0, 4.0, 2.0], 3, FLOAT32) }),
  (:Node { id: 2, vector: vector([3.0, -2.0, 1.0], 3, FLOAT32) }),
  (:Node { id: 3, vector: vector([2.0, 8.0, 3.0], 3, FLOAT32) });
```

Given a parameter `query` (here set to `[4.0, 5.0, 6.0]`), you can query for the two nearest neighbors by Euclidean distance. This is achieved by matching on all candidate vectors and ordering by the similarity score:

```cypher
MATCH (node:Node)
WITH node, vector.similarity.euclidean($query, node.vector) AS score
RETURN node, score
ORDER BY score DESCENDING
LIMIT 2
```

This returns the two nearest neighbors.


| node | score |
| --- | --- |
|
`(:Node {vector: vector([2.0, 8.0, 3.0], 3, FLOAT32 NOT NULL), id: 3})`

 |

`0.043478261679410934`

 |
|

`(:Node {vector: vector([1.0, 4.0, 2.0], 3, FLOAT32 NOT NULL), id: 1})`

 |

`0.03703703731298447`

 |
|

Rows: 2

 |

## [](https://neo4j.com/docs/cypher-manual/current/functions/vector/#functions-vector_dimension_count)vector\_dimension\_count()

Cypher 25 onlyIntroduced in Neo4j 2025.10

<table class="tableblock frame-all grid-all stretch"><caption class="title">Details</caption> <colgroup><col style="width: 25%;"> <col style="width: 25%;"> <col style="width: 25%;"> <col style="width: 25%;"></colgroup><tbody><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Syntax</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock"><code>vector_dimension_count(vector)</code></p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Description</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock">Returns the dimension of a <code>VECTOR</code>.</p></td></tr><tr><td class="tableblock halign-left valign-top" rowspan="2"><p class="tableblock"><strong>Arguments</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Name</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Type</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Description</strong></p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vector</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>VECTOR</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">The vector to calculate the dimension of.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Returns</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock"><code>INTEGER</code></p></td></tr></tbody></table>

<table><tbody><tr><td class="icon"><i class="fa icon-tip" title="Tip"></i></td><td class="content">You can also use the <a href="https://neo4j.com/docs/cypher-manual/current/functions/scalar/#functions-size" class="xref page"><code>size()</code></a> function to return the dimension of a <code>VECTOR</code> value.</td></tr></tbody></table>

Example 5. Calculate the size of a `VECTOR`

Query

```cypher
RETURN vector_dimension_count(vector([1, 2, 3], 3, INTEGER8)) AS size
```

Result
| size |
| --- |
|
`3`

 |
|

Rows: 1

 |

## [](https://neo4j.com/docs/cypher-manual/current/functions/vector/#functions-vector_distance)vector\_distance()

Cypher 25 onlyIntroduced in Neo4j 2025.10

<table class="tableblock frame-all grid-all stretch"><caption class="title">Details</caption> <colgroup><col style="width: 25%;"> <col style="width: 25%;"> <col style="width: 25%;"> <col style="width: 25%;"></colgroup><tbody><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Syntax</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock"><code>vector_distance(vector1, vector2, vectorDistanceMetric)</code></p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Description</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock">Returns a <code>FLOAT</code> representing the distance between the two vector values based on the selected <code>vectorDistanceMetric</code> algorithm.</p></td></tr><tr><td class="tableblock halign-left valign-top" rowspan="4"><p class="tableblock"><strong>Arguments</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Name</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Type</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Description</strong></p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vector1</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>VECTOR</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">The first vector.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vector2</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>VECTOR</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">The second vector.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vectorDistanceMetric</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>[EUCLIDEAN, EUCLIDEAN_SQUARED, MANHATTAN, COSINE, DOT, HAMMING]</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">The vector distance algorithm to calculate the distance by.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Returns</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock"><code>FLOAT</code></p></td></tr></tbody></table>

Supported `vectorDistanceMetric` algorithms
| Distance Type | Formula |
| --- | --- |
|
`EUCLIDEAN`

 |

√( (A₁ - B₁)² + (A₂ - B₂)² + …​ + (Aᴰ - Bᴰ)² )

 |
|

`EUCLIDEAN_SQUARED`

 |

(A₁ - B₁)² + (A₂ - B₂)² + …​ + (Aᴰ - Bᴰ)²

 |
|

`MANHATTAN`

 |

|A₁ - B₁| + |A₂ - B₂| + …​ + |Aᴰ - Bᴰ|

 |
|

`COSINE`

 |

1 - ( (A₁×B₁ + A₂×B₂ + …​ + Aᴰ×Bᴰ) / ( √(A₁² + A₂² + …​ + Aᴰ²) × √(B₁² + B₂² + …​ + Bᴰ²) ) )

 |
|

`DOT`

 |

\- (A₁×B₁ + A₂×B₂ + …​ + Aᴰ×Bᴰ)

 |
|

`HAMMING`

 |

Number of dimensions in which `vector1` and `vector2` differ.

 |

<table class="tableblock frame-all grid-all stretch"><caption class="title">Considerations</caption> <colgroup><col style="width: 100%;"></colgroup><tbody><tr><td class="tableblock halign-left valign-top"><p class="tableblock">The smaller the returned number, the more similar the vectors; the larger the number, the more distant the vectors. This is in contrast to the similarity functions where the closer to <code>1</code> the result is the higher the degree of similarity.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock">Floating point operations are performed with <code>float32</code> arithmetic.</p></td></tr></tbody></table>

Example 6. Calculate the distance between two vectors using the `COSINE` distance

Query

```cypher
RETURN vector_distance(vector([1, 2, 3], 3, INTEGER8), vector([1, 2, 4], 3, INTEGER8), COSINE) AS distance
```

Result
| distance |
| --- |
|
`0.008539855480194092`

 |
|

Rows: 1

 |

Example 7. Calculate the distance between two vectors using the `EUCLIDEAN` distance

Query

```cypher
RETURN vector_distance(vector([1.0, 5.0, 3.0, 6.7], 4, FLOAT32), vector([5.0, 2.5, 3.1, 9.0], 4, FLOAT32), EUCLIDEAN)
```

Result
| distance |
| --- |
|
`5.248809337615967`

 |
|

Rows: 1

 |

## [](https://neo4j.com/docs/cypher-manual/current/functions/vector/#functions-vector_norm)vector\_norm()

Cypher 25 onlyIntroduced in Neo4j 2025.20

<table class="tableblock frame-all grid-all stretch"><caption class="title">Details</caption> <colgroup><col style="width: 25%;"> <col style="width: 25%;"> <col style="width: 25%;"> <col style="width: 25%;"></colgroup><tbody><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Syntax</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock"><code>vector_norm(vector, vectorDistanceMetric)</code></p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Description</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock">Returns a <code>FLOAT</code> representing the distance between the given vector and an origin vector, which is a vector with the same dimension with all coordinates set to zero, calculated using the specified <code>vectorDistanceMetric</code>.</p></td></tr><tr><td class="tableblock halign-left valign-top" rowspan="3"><p class="tableblock"><strong>Arguments</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Name</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Type</strong></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Description</strong></p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vector</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>VECTOR</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">A vector for which the norm to the origin vector will be computed.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><code>vectorDistanceMetric</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock"><code>[EUCLIDEAN, MANHATTAN]</code></p></td><td class="tableblock halign-left valign-top"><p class="tableblock">The vector distance algorithm to calculate the distance by.</p></td></tr><tr><td class="tableblock halign-left valign-top"><p class="tableblock"><strong>Returns</strong></p></td><td class="tableblock halign-left valign-top" colspan="3"><p class="tableblock"><code>FLOAT</code></p></td></tr></tbody></table>

Supported `vectorDistanceMetric` algorithms
| Distance Type | Formula |
| --- | --- |
|
`EUCLIDEAN`

 |

√( (A₁ - B₁)² + (A₂ - B₂)² + …​ + (Aᴰ - Bᴰ)² )

 |
|

`MANHATTAN`

 |

|A₁ - B₁| + |A₂ - B₂| + …​ + |Aᴰ - Bᴰ|

 |

Example 8. Measure the norm between a vector and an origin vector using the `EUCLIDEAN` distance

<table class="tableblock frame-all grid-all stretch"><caption class="title">Considerations</caption> <colgroup><col style="width: 100%;"></colgroup><tbody><tr><td class="tableblock halign-left valign-top"><p class="tableblock">Floating point operations are performed with <code>float32</code> arithmetic.</p></td></tr></tbody></table>

Query

```cypher
RETURN vector_norm(vector([1.0, 5.0, 3.0, 6.7], 4, FLOAT32), EUCLIDEAN) AS norm
```

Result
| norm |
| --- |
|
`8.93812084197998`

 |
|

Rows: 1

 |

Example 9. Measure the norm between a vector and an origin vector using the `EUCLIDEAN` distance

Query

```cypher
RETURN vector_norm(vector([1.0, 5.0, 3.0, 6.7], 4, FLOAT32), MANHATTAN) AS norm
```

Result
| norm |
| --- |
|
`15.699999809265137`

 |
|

Rows: 1

 |
