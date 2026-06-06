package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
)

type Node struct {
	ID string `json:"id"`
	IP string `json:"ip"`
}

type Workload struct {
	ProjectName string `json:"project_name"`
	ComputeSize string `json:"compute_size"`
}

var (
	nodes = make(map[string]Node)
	nodesMutex sync.RWMutex
)

func pickRandomNode() (*Node, error) {
	nodesMutex.RLock()
	defer nodesMutex.RUnlock()

	if len(nodes) == 0 {
		return nil, fmt.Errorf("no nodes currently online")
	}

	for _, node := range nodes {
		return &node, nil
	}

	return nil, fmt.Errorf("failed to schedule node")
}

func registerNodeHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Only POST allowed", http.StatusMethodNotAllowed)
		return
	}

	var newNode Node

	if err := json.NewDecoder(r.Body).Decode(&newNode); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	nodesMutex.Lock()
	nodes[newNode.ID] = newNode
	nodesMutex.Unlock()

	fmt.Printf("Node registered at: %s at %s\n", newNode.ID, newNode.IP)
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]string{"message": "bruzz node registered successfully"})
}

func deployHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST request required", http.StatusMethodNotAllowed)
		return
	}

	var workload Workload
	if err := json.NewDecoder(r.Body).Decode(&workload); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	assignedNode, err := pickRandomNode()
	if err != nil {
		http.Error(w, err.Error(), http.StatusServiceUnavailable)
		return
	}

	fmt.Printf("Deploying '%s' to Node %s (%s)\n", workload.ProjectName, assignedNode.ID, assignedNode.IP)

	response := map[string]string {
		"status": "deployed",
		"workload_id": "tandem-workload-" + assignedNode.ID[:4],
		"assigned_to": assignedNode.ID,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func main() {
	mux := http.NewServeMux()

	mux.HandleFunc("/register", registerNodeHandler)
	mux.HandleFunc("/deploy", deployHandler)

	fmt.Println("Running on http://localhost:6767")
	log.Fatal(http.ListenAndServe(":6767", mux))
}