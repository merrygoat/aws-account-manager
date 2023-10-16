function delete_selected_rows(url) {
    const selectedRows = gridOptions.api.getSelectedRows()
    fetch(url, {
        method: "DELETE",
        body: JSON.stringify(selectedRows),
        headers: {"Content-type": "application/json; charset=UTF-8"}
    }).then(function (response) {
        if (response.ok) {
            gridOptions.api.applyTransaction({remove: selectedRows})
        } else {
            console.log("Error deleting data.")
        }
    })
}

function add_empty_row() {
    gridOptions.api.applyTransaction({add: [{id: -1}]})
}

function row_edited(event, url) {
    if (event.node.id === '-1') {
        add_new_record(event, url)
    } else {
        update_record(event, url)
    }
}

function update_record(event, url) {
    fetch(url, {
        method: "PUT",
        body: JSON.stringify(event.data),
        headers: {"Content-type": "application/json; charset=UTF-8"}
    }).then(function (response) {
        if (response.ok) {
            return response.json();
        }
    })
}

function add_new_record(event, url) {
    fetch(url, {
        method: "POST",
        body: JSON.stringify(event.data),
        headers: {"Content-type": "application/json; charset=UTF-8"}
    }).then(function (response) {
        if (response.ok) {
            return response.json();
        }
    }).then(function (response_data) {
            let new_row = event.node.data
            new_row["id"] = response_data["id"]
            gridOptions.api.applyTransaction({remove: [{id: -1}]})
            gridOptions.api.applyTransaction({add: [new_row]})
        }
    )
}

function fetch_data(url) {
    fetch(url
    ).then(function (response) {
        return response.json();
    }).then(function (data) {
        gridOptions.api.setRowData(data);
    });
}

function initialise_grid() {
    // Set up the grid after the page has finished loading
    document.addEventListener('DOMContentLoaded', () => {
        const gridDiv = document.querySelector('#page_grid');
        new agGrid.Grid(gridDiv, gridOptions);
    });
}
