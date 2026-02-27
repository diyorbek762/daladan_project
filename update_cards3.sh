#!/bin/bash
awk '
/addToCart\('\''Golden Apples'\'', 0.45, '\''Farruh M.'\''\)/ {
    print "                        <div style=\"margin-top:0.8rem;padding:0.4rem;border-radius:6px;background:#ECFDF5;color:#059669;font-size:0.75rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;\"><i class=\"fa-solid fa-truck-fast\"></i> Seller offers delivery</div>";
    print "                        <button class=\"market-card-btn\" onclick=\"addToCart('\''Golden Apples'\'', 0.45, '\''Farruh M.'\'', '\''+998901234567'\'', true)\">";
    next;
}
/addToCart\('\''Navot Melons'\'', 0.80, '\''Ali N.'\''\)/ {
    print "                        <div style=\"margin-top:0.8rem;padding:0.4rem;border-radius:6px;background:#EFF6FF;color:#2563EB;font-size:0.75rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;\"><i class=\"fa-solid fa-user-clock\"></i> Requires driver assignment</div>";
    print "                        <button class=\"market-card-btn\" onclick=\"addToCart('\''Navot Melons'\'', 0.80, '\''Ali N.'\'', '\''+998939876543'\'', false)\">";
    next;
}
/addToCart\('\''Red Tomatoes'\'', 0.30, '\''Dilshod T.'\''\)/ {
    print "                        <div style=\"margin-top:0.8rem;padding:0.4rem;border-radius:6px;background:#EFF6FF;color:#2563EB;font-size:0.75rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;\"><i class=\"fa-solid fa-user-clock\"></i> Requires driver assignment</div>";
    print "                        <button class=\"market-card-btn\" onclick=\"addToCart('\''Red Tomatoes'\'', 0.30, '\''Dilshod T.'\'', '\''+998993214567'\'', false)\">";
    next;
}
/addToCart\('\''Yellow Onions'\'', 0.20, '\''Otabek Z.'\''\)/ {
    print "                        <div style=\"margin-top:0.8rem;padding:0.4rem;border-radius:6px;background:#ECFDF5;color:#059669;font-size:0.75rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;\"><i class=\"fa-solid fa-truck-fast\"></i> Seller offers delivery</div>";
    print "                        <button class=\"market-card-btn\" onclick=\"addToCart('\''Yellow Onions'\'', 0.20, '\''Otabek Z.'\'', '\''+998918887766'\'', true)\">";
    next;
}
{ print }
' index.html > temp.html && mv temp.html index.html

awk '
/<button type="submit"/ {
    if (!done) {
        print "                    <div style=\"margin-bottom:1.5rem;display:flex;align-items:center;gap:0.5rem;\">";
        print "                        <input type=\"checkbox\" id=\"harvest-transport\" style=\"width:1rem;height:1rem;accent-color:var(--agro-green);\">";
        print "                        <label for=\"harvest-transport\" style=\"font-size:0.85rem;color:var(--text-primary);cursor:pointer;\">";
        print "                            I can transport this myself <span style=\"color:var(--text-secondary);\">(Include transport fee in price)</span>";
        print "                        </label>";
        print "                    </div>";
        print "                    <button type=\"submit\"";
        done = 1;
        next;
    }
}
{ print }
' index.html > temp2.html && mv temp2.html index.html

