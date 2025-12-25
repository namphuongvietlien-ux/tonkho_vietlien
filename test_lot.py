from convert_to_json import parse_lot_to_date, calculate_remaining_percentage
from datetime import datetime

# Test LOT 2805
expiry = parse_lot_to_date('2805')
print(f'LOT 2805 -> Ngày hết hạn: {expiry.strftime("%d/%m/%Y")}')

pct, expiry_str = calculate_remaining_percentage('2805', 36)
print(f'Thời hạn: 36 tháng')
print(f'% còn lại: {pct}%')
print(f'Ngày hết hạn: {expiry_str}')
print(f'Hôm nay: {datetime.now().strftime("%d/%m/%Y")}')
