import re

with open('index.html', 'r') as f:
    content = f.read()

# 1. Driver Board
driver_board = """                    <!-- Available Transport Jobs (Dynamically Populated) -->
                    <div class="content-card" style="margin-bottom: 1.5rem;" id="available-freight-container">
                        <div class="content-card-header">
                            <span class="content-card-title"><i class="fa-solid fa-box-open" style="color:var(--harvest-amber);margin-right:0.5rem;"></i>Available Transport Jobs</span>
                            <span class="content-card-badge" id="freight-badge" style="background:#FFFBEB;color:var(--harvest-amber);display:none;">0 New</span>
                        </div>
                        <div id="freight-list">
                            <div style="text-align:center;padding:1rem;color:var(--text-secondary);font-size:0.85rem;" id="no-freight-msg">
                                No available jobs at the moment.
                            </div>
                        </div>
                    </div>

                    <!-- Delivery List -->"""
content = content.replace("                    <!-- Delivery List -->", driver_board, 1)

# 2. Harvest Checkbox
harvest_checkbox = """                        <input type="number" id="harvest-price" required min="1" step="0.01"
                            style="width:100%;padding:0.75rem;border:1px solid var(--border-color);border-radius:var(--radius-md);outline:none;background:var(--card-bg);color:var(--text-primary);"
                            placeholder="e.g. 4500">
                    </div>
                    <div style="margin-bottom:1.5rem;display:flex;align-items:center;gap:0.5rem;">
                        <input type="checkbox" id="harvest-transport" style="width:1rem;height:1rem;accent-color:var(--agro-green);">
                        <label for="harvest-transport" style="font-size:0.85rem;color:var(--text-primary);cursor:pointer;">
                            I can transport this myself <span style="color:var(--text-secondary);">(Include transport fee in price)</span>
                        </label>
                    </div>
                    <button type="submit"
                        style="width:100%;padding:0.875rem;background:var(--agro-green);color:white;border:none;border-radius:var(--radius-md);font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:0.5rem;transition:background 0.2s;">
                        <i class="fa-solid fa-plus"></i> Add to Inventory"""

old_harvest = """                        <input type="number" id="harvest-price" required min="1" step="0.01"
                            style="width:100%;padding:0.75rem;border:1px solid var(--border-color);border-radius:var(--radius-md);outline:none;background:var(--card-bg);color:var(--text-primary);"
                            placeholder="e.g. 4500">
                    </div>
                    <button type="submit"
                        style="width:100%;padding:0.875rem;background:var(--agro-green);color:white;border:none;border-radius:var(--radius-md);font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:0.5rem;transition:background 0.2s;">
                        <i class="fa-solid fa-plus"></i> Add to Inventory"""
content = content.replace(old_harvest, harvest_checkbox, 1)

# 3. Product Cards
content = content.replace(
    """<button class="market-card-btn" onclick="addToCart('Golden Apples', 0.45, 'Farruh M.')">""",
    """<div style="margin-top:0.8rem;padding:0.4rem;border-radius:6px;background:#ECFDF5;color:#059669;font-size:0.75rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;">
                            <i class="fa-solid fa-truck-fast"></i> Seller offers delivery
                        </div>
                        <button class="market-card-btn" onclick="addToCart('Golden Apples', 0.45, 'Farruh M.', '+998901234567', true)">"""
)
content = content.replace(
    """<button class="market-card-btn" onclick="addToCart('Navot Melons', 0.80, 'Ali N.')">""",
    """<div style="margin-top:0.8rem;padding:0.4rem;border-radius:6px;background:#EFF6FF;color:#2563EB;font-size:0.75rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;">
                            <i class="fa-solid fa-user-clock"></i> Requires driver assignment
                        </div>
                        <button class="market-card-btn" onclick="addToCart('Navot Melons', 0.80, 'Ali N.', '+998939876543', false)">"""
)
content = content.replace(
    """<button class="market-card-btn" onclick="addToCart('Red Tomatoes', 0.30, 'Dilshod T.')">""",
    """<div style="margin-top:0.8rem;padding:0.4rem;border-radius:6px;background:#EFF6FF;color:#2563EB;font-size:0.75rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;">
                            <i class="fa-solid fa-user-clock"></i> Requires driver assignment
                        </div>
                        <button class="market-card-btn" onclick="addToCart('Red Tomatoes', 0.30, 'Dilshod T.', '+998993214567', false)">"""
)
content = content.replace(
    """<button class="market-card-btn" onclick="addToCart('Yellow Onions', 0.20, 'Otabek Z.')">""",
    """<div style="margin-top:0.8rem;padding:0.4rem;border-radius:6px;background:#ECFDF5;color:#059669;font-size:0.75rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;">
                            <i class="fa-solid fa-truck-fast"></i> Seller offers delivery
                        </div>
                        <button class="market-card-btn" onclick="addToCart('Yellow Onions', 0.20, 'Otabek Z.', '+998918887766', true)">"""
)

# 4. Payment Modal HTML
payment_modal = """    <!-- Payment Checkout Modal -->
    <div class="modal-overlay" id="payment-modal" onclick="if(event.target===this)closePaymentModal()">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-header-left">
                    <span class="icon-bg" style="background:#ECFDF5;color:var(--agro-green);"><i class="fa-solid fa-credit-card"></i></span>
                    <h2 style="font-size:1.1rem;margin:0;">Finalize Payment</h2>
                </div>
                <button class="modal-close" onclick="closePaymentModal()">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
            <div class="modal-body" style="padding:1.5rem;">
                <div style="text-align:center;margin-bottom:1.5rem;">
                    <div style="font-size:0.9rem;color:var(--text-secondary);margin-bottom:0.25rem;">Total Amount to Escrow</div>
                    <div style="font-size:2rem;font-weight:700;color:var(--text-primary);" id="payment-total">$0.00</div>
                </div>
                
                <div style="background:var(--bg-color);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:1rem;margin-bottom:1.5rem;">
                    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.5rem;">
                        <i class="fa-solid fa-lock" style="color:var(--text-secondary);"></i>
                        <div style="font-size:0.9rem;font-weight:600;">Secure Escrow Hold</div>
                    </div>
                    <div style="font-size:0.8rem;color:var(--text-secondary);line-height:1.4;">
                        Your funds will be held securely in a smart contract. The seller is instantly notified, and funds are only released upon your confirmation of delivery.
                    </div>
                </div>

                <div style="margin-bottom:1.5rem;">
                    <label style="display:block;margin-bottom:0.5rem;font-size:0.85rem;color:var(--text-secondary);">Select Payment Method</label>
                    <select style="width:100%;padding:0.75rem;border:1px solid var(--border-color);border-radius:var(--radius-md);outline:none;background:var(--card-bg);color:var(--text-primary);">
                        <option value="bank">Bank Transfer (UzPSB) ending in 4022</option>
                        <option value="corporate">Corporate Card ending in 8812</option>
                    </select>
                </div>

                <button onclick="confirmPayment()" id="confirm-payment-btn" style="width:100%;padding:0.875rem;background:var(--agro-green);color:white;border:none;border-radius:var(--radius-md);font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:0.5rem;transition:background 0.2s;">
                    <i class="fa-solid fa-check-circle"></i> Confirm Payment
                </button>
            </div>
        </div>
    </div>

    <!-- ═══ Greedy Algorithm Modal ═══ -->"""
content = content.replace("    <!-- ═══ Greedy Algorithm Modal ═══ -->", payment_modal, 1)

# 5. Overwrite Checkout Logic
old_btn = """                <button onclick="proceedToEscrow()" style="width:100%;padding:0.875rem;background:var(--accent-blue);color:white;border:none;border-radius:var(--radius-md);font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:0.5rem;transition:background 0.2s;">"""
new_btn = """                <button onclick="openPaymentModal()" style="width:100%;padding:0.875rem;background:var(--accent-blue);color:white;border:none;border-radius:var(--radius-md);font-weight:600;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:0.5rem;transition:background 0.2s;">"""
content = content.replace(old_btn, new_btn)

# Add parameters to addToCart signature
content = content.replace("function addToCart(name, price, seller) {", "function addToCart(name, price, seller, phone = '+998XXXXXXXXX', producerTransport = false) {")
content = content.replace("cart.push({ name, price, seller, quantity: 100 });", "cart.push({ name, price, seller, phone, producerTransport, quantity: 100 });")


js_checkout = """        function closeCartModal() {
            document.getElementById('cart-modal').classList.remove('open');
        }

        let cartTotalValue = 0;

        function openPaymentModal() {
            if (cart.length === 0) {
                showToast('Cart is empty!', 'error');
                return;
            }
            
            // Calculate total for payment modal
            cartTotalValue = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
            document.getElementById('payment-total').innerText = '$' + cartTotalValue.toFixed(2);
            
            closeCartModal();
            document.getElementById('payment-modal').classList.add('open');
        }

        function closePaymentModal() {
            document.getElementById('payment-modal').classList.remove('open');
        }

        function confirmPayment() {
            const btn = document.getElementById('confirm-payment-btn');
            const originalText = btn.innerHTML;
            
            // Show loading state
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing Payment...';
            btn.style.opacity = '0.8';
            btn.disabled = true;
            
            setTimeout(() => {
                let driverJobCreated = false;
                
                // Generate deals & jobs for each item
                cart.forEach(item => {
                    const dealId = 'deal-' + Math.floor(Math.random() * 10000);
                    
                    // 1. Setup new chat interface for the deal
                    setupNewDealChat(item, dealId);
                    
                    // 2. If producer doesn't handle transport, post to Driver board
                    if (!item.producerTransport) {
                        postToDriverBoard(item, dealId);
                        driverJobCreated = true;
                    }
                });

                closePaymentModal();
                btn.innerHTML = originalText;
                btn.style.opacity = '1';
                btn.disabled = false;
                
                cart = []; // Clear cart

                const badge = document.getElementById('cart-badge');
                if (badge) {
                    badge.innerText = '0';
                    badge.style.display = 'none';
                }

                showToast('Payment successful! Escrow initialized.', 'success', 2000);
                
                if (driverJobCreated) {
                    setTimeout(() => {
                        showToast('Driver network notified of new available job!', 'info', 3000);
                    }, 500);
                }

                setTimeout(() => {
                    switchView('messages');
                }, 1500);
                
            }, 1200); // Simulate network delay
        }

        // --- Checkout Flow Helpers ---
        function setupNewDealChat(item, dealId) {
            const list = document.getElementById('deal-groups-list');
            const totalEscrow = (item.price * item.quantity).toFixed(2);
            
            // 1. Add to Sidebar Left
            const sidebarHTML = `
                <div class="chat-contact" onclick="document.querySelectorAll('.chat-contact').forEach(el=>el.classList.remove('active')); this.classList.add('active');" style="animation: fadeInUp 0.4s ease forwards;">
                    <div class="contact-avatar" style="background:#ECFDF5;color:#059669;">
                        <i class="fa-solid fa-leaf"></i>
                    </div>
                    <div class="contact-info">
                        <div class="contact-name">${item.seller}</div>
                        <div class="contact-preview">Order: ${item.quantity}kg ${item.name}</div>
                    </div>
                </div>
            `;
            list.insertAdjacentHTML('afterbegin', sidebarHTML);

            // 2. Populate Chat Body dynamically
            // Overwriting existing chat display for simulation purposes
            const chatBodyHTML = `
                <div class="message system">
                    <div class="system-inner">
                        <i class="fa-solid fa-shield-halved" style="color:var(--accent-blue);font-size:1.2rem;margin-bottom:0.5rem;"></i>
                        <h4 style="margin:0 0 0.5rem 0;color:var(--text-primary);">Escrow Transaction Initialized</h4>
                        <p style="margin:0;font-size:0.85rem;">
                            <strong>Order:</strong> ${item.quantity} kg ${item.name}<br>
                            <strong>Escrow Held:</strong> $${totalEscrow} (Funds are secured until delivery)<br>
                            <strong>Seller Phone:</strong> ${item.phone}<br>
                            <strong>Transport:</strong> ${item.producerTransport ? 'Handled by Seller' : 'Awaiting Driver Assignment'}
                        </p>
                    </div>
                </div>
                
                <div class="message received" style="animation: fadeInUp 0.3s ease forwards; animation-delay: 0.5s; opacity:0;">
                    <div class="msg-avatar" style="background:#ECFDF5;color:#059669;">
                        <i class="fa-solid fa-leaf"></i>
                    </div>
                    <div class="msg-bubble">
                        Assalomu alaykum! I have received your secure escrow deposit for $${totalEscrow}. The ${item.name} are ready for pickup.
                        <div class="msg-time">Just now</div>
                    </div>
                </div>
            `;
            
            const chatBody = document.getElementById('chat-body');
            if (chatBody) {
                // Remove placeholder messages, leave date header
                const items = Array.from(chatBody.children);
                items.forEach(el => {
                    if(!el.classList.contains('chat-date-divider')) el.remove();
                });
                chatBody.insertAdjacentHTML('beforeend', chatBodyHTML);
                // Trigger reflow & jump to bottom
                setTimeout(() => { chatBody.scrollTop = chatBody.scrollHeight; }, 100);
            }
        }

        function postToDriverBoard(item, dealId) {
            const container = document.getElementById('freight-list');
            const badge = document.getElementById('freight-badge');
            const noMsg = document.getElementById('no-freight-msg');
            
            if (noMsg) noMsg.style.display = 'none';
            
            // Random route for simulation
            const routes = ["Samarkand &rarr; Tashkent", "Fergana &rarr; Andijan", "Bukhara &rarr; Navoi"];
            const route = routes[Math.floor(Math.random() * routes.length)];
            const payout = Math.floor(item.quantity * 0.12); // ~12c per kg driver payout simulation

            const jobHTML = `
                <div class="placeholder-row" id="${dealId}" style="animation: fadeInUp 0.4s ease forwards;">
                    <div class="placeholder-avatar" style="background:var(--harvest-amber);color:white;">
                        <i class="fa-solid fa-sack-dollar"></i>
                    </div>
                    <div class="placeholder-text">
                        <div class="name">${item.quantity} kg ${item.name}</div>
                        <div class="desc">${route} &bull; Driver Payout: $${payout}</div>
                    </div>
                    <button onclick="acceptFreight('${dealId}', '${item.name}')" style="padding: 0.4rem 0.8rem; border-radius: 8px; border: none; background: var(--agro-green); color: white; font-weight: 600; cursor: pointer; font-size: 0.75rem; transition: background 0.2s;">
                        Accept Load
                    </button>
                </div>
            `;
            
            if (container) {
                container.insertAdjacentHTML('afterbegin', jobHTML);
            }
            
            if (badge) {
                let current = parseInt(badge.innerText) || 0;
                badge.innerText = `${current + 1} New`;
                badge.style.display = 'inline-flex';
            }
        }"""

old_js_checkout = re.compile(
    r"        function closeCartModal\(\) \{\n.*?\}\n\n        function proceedToEscrow\(\) \{.*?\n        \}",
    re.DOTALL
)
content = old_js_checkout.sub(js_checkout, content)


with open('index.html', 'w') as f:
    f.write(content)
