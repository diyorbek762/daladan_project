#!/bin/bash
awk '
/addToCart\('\''Golden Apples'\'', 0.45, '\''Farruh M.'\''\)/ {
    print "                        <div style=\"margin-top:0.8rem;padding:0.4rem;border-radius:6px;background:#ECFDF5;color:#059669;font-size:0.75rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;\">";
    print "                            <i class=\"fa-solid fa-truck-fast\"></i> Seller offers delivery";
    print "                        </div>";
    print "                        <button class=\"market-card-btn\" onclick=\"addToCart('\''Golden Apples'\'', 0.45, '\''Farruh M.'\'', '\''+998901234567'\'', true)\">";
    next;
}
/addToCart\('\''Navot Melons'\'', 0.80, '\''Ali N.'\''\)/ {
    print "                        <div style=\"margin-top:0.8rem;padding:0.4rem;border-radius:6px;background:#EFF6FF;color:#2563EB;font-size:0.75rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;\">";
    print "                            <i class=\"fa-solid fa-user-clock\"></i> Requires driver assignment";
    print "                        </div>";
    print "                        <button class=\"market-card-btn\" onclick=\"addToCart('\''Navot Melons'\'', 0.80, '\''Ali N.'\'', '\''+998939876543'\'', false)\">";
    next;
}
/addToCart\('\''Red Tomatoes'\'', 0.30, '\''Dilshod T.'\''\)/ {
    print "                        <div style=\"margin-top:0.8rem;padding:0.4rem;border-radius:6px;background:#EFF6FF;color:#2563EB;font-size:0.75rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;\">";
    print "                            <i class=\"fa-solid fa-user-clock\"></i> Requires driver assignment";
    print "                        </div>";
    print "                        <button class=\"market-card-btn\" onclick=\"addToCart('\''Red Tomatoes'\'', 0.30, '\''Dilshod T.'\'', '\''+998993214567'\'', false)\">";
    next;
}
/addToCart\('\''Yellow Onions'\'', 0.20, '\''Otabek Z.'\''\)/ {
    print "                        <div style=\"margin-top:0.8rem;padding:0.4rem;border-radius:6px;background:#ECFDF5;color:#059669;font-size:0.75rem;font-weight:600;display:flex;align-items:center;gap:0.4rem;\">";
    print "                            <i class=\"fa-solid fa-truck-fast\"></i> Seller offers delivery";
    print "                        </div>";
    print "                        <button class=\"market-card-btn\" onclick=\"addToCart('\''Yellow Onions'\'', 0.20, '\''Otabek Z.'\'', '\''+998918887766'\'', true)\">";
    next;
}
{ print }
' index.html > temp2.html && mv temp2.html index.html
