"""Conditional component-capacity sensitivity scenarios, not field soil moisture."""
import math
from . import InvalidInputError, MissingInputError


def adapt_ssurgo(data):
    area = {str(m['mapunit_id']): float(m['aoi_fraction']) for m in data['mapunits']}
    if any(not math.isfinite(a) or a < 0 for a in area.values()) or sum(area.values()) > 1.001:
        raise InvalidInputError('Invalid mapped AOI fractions')
    per_unit = {k: 0.0 for k in area}
    weighted = []
    missing_mass = 1.0 - sum(area.values())
    for c in data['components']:
        key = str(c['mapunit_id'])
        fraction = float(c['component_fraction'])
        if key not in area or not math.isfinite(fraction) or fraction < 0 or fraction > 1:
            raise InvalidInputError('Invalid SSURGO component fraction/mapunit')
        per_unit[key] += fraction
        weight = area[key] * fraction
        storage = c.get('estimated_storage_mm')
        if storage is None:
            missing_mass += weight
            continue
        storage = float(storage)
        if not math.isfinite(storage) or storage <= 0 or storage > 1000:
            raise InvalidInputError('Invalid SSURGO storage capacity')
        if c.get('target_depth_cm') != 100:
            raise InvalidInputError('Unexpected soil integration target')
        weighted.append((storage, weight, key, c['component_id']))
    if any(v > 1.001 for v in per_unit.values()):
        raise InvalidInputError('Component fractions exceed 1 for mapunit')
    missing_mass += sum(area[k] * (1 - v) for k, v in per_unit.items())
    known = sum(w for _, w, _, _ in weighted)
    if known < 0.5:
        raise MissingInputError('Insufficient mapped component mass for conditional scenarios')
    def quantile(q):
        target = q * known
        accum = 0
        for value, weight, _, _ in sorted(weighted):
            accum += weight
            if accum >= target:
                return value
        return max(v for v, *_ in weighted)
    values = {'low_storage': quantile(.1), 'medium_storage': quantile(.5), 'high_storage': quantile(.9)}
    return {'scenarios': {k: {'value': v, 'status': 'ssurgo_component_capacity_conditional_sensitivity'} for k,v in values.items()},
            'source': 'SSURGO component-capacity weighted quantiles (10/50/90), conditional on mapped known mass; 100 cm assumed integration target',
            'known_aoi_component_mass': known, 'unknown_aoi_component_mass': missing_mass,
            'component_count': len(weighted), 'method': 'area_fraction * component_fraction; weighted conditional discrete quantiles; missing mass not allocated'}
