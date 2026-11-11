def queue_order(tickets):
    ranked = sorted(tickets, key=lambda ticket: ticket[1])[::-1]
    return [ticket_id for ticket_id, _ in ranked]
