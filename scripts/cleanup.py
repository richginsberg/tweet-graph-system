"""Quick script to delete all tweets with zero embeddings"""

from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "tweetgraph123"))

with driver.session() as session:
    # Delete all tweets
    result = session.run("MATCH (t:Tweet) DETACH DELETE t RETURN count(t) as deleted")
    deleted = result.single()["deleted"]
    print(f"Deleted {deleted} tweets")

driver.close()
