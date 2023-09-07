function remember_active_tab(default_tab_id) {
    // Script to set active bootstrap tab on page reload.
    let activePage = sessionStorage.getItem('activePage')
    let activeTab = sessionStorage.getItem('activeTab')
    if (activePage === document.URL && activeTab) {
        new bootstrap.Tab(document.querySelector(`#${activeTab}`)).show()
        }
    else {
        new bootstrap.Tab(document.querySelector(`#${default_tab_id}`)).show()
    }

    document.addEventListener("shown.bs.tab", function (e) {
        sessionStorage.setItem('activeTab', e.target.id)
        sessionStorage.setItem('activePage', document.URL)
    })
}
