package ch.unisg.scs.edpo.factory.domain;

import lombok.NonNull;
import java.util.List;

public record FetchInventoryDto(@NonNull List<InventoryPositionDto> fetched) {
	public List<InventoryPositionDto> positions() {
		return fetched;
	}
}
