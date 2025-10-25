if (window.location.href.includes('/my/rmas/create_view')) {
    const originPickingDropdown = document.getElementById('origin_picking');
    const originMoveDropdown = document.getElementById('origin_move');
    const quantityInput = document.getElementById('quantity');
    const fetchUrl_picking = originPickingDropdown.getAttribute('data-fetch-url');
    const fetchUrl_moves = originMoveDropdown.getAttribute('data-fetch-url');

    originPickingDropdown.addEventListener('change', () => {
        const pickingId = originPickingDropdown.value;

        fetch(fetchUrl_picking, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json', // Specify JSON content type
            },
            body: JSON.stringify({ params: { picking_id: pickingId } }) // Send picking_id inside params
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
    .then(data => {
        if (!data.result || !Array.isArray(data.result)) {
            console.error('Expected an array in the "result" field but received:', data);
            alert('Error: Server returned an unexpected response.');
            return;
        }
      const lines = data.result;
        originMoveDropdown.innerHTML = '';

        lines.forEach(line => {
            const option = document.createElement('option');
            option.value = line.id;
            option.textContent = `${line.product_id.display_name}`;
            originMoveDropdown.appendChild(option);
        });
        if (lines)
            quantityInput.value = lines[0].quantity;

    })
        .catch(error => {
            console.error('Error fetching picking lines:', error);
        });
    });



        originMoveDropdown.addEventListener('change', () => {
        const move_id = originMoveDropdown.value;

        fetch(fetchUrl_moves, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json', // Specify JSON content type
            },
            body: JSON.stringify({ params: { move_id: move_id } }) // Send picking_id inside params
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
    .then(data => {
        quantityInput.value = data.result.quantity;
    })
        .catch(error => {
            console.error('Error fetching picking lines:', error);
        });
    });

}
